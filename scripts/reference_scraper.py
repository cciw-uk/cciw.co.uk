#!/usr/bin/env python
import re
import sys
import datetime
from subprocess import Popen, PIPE

# Questions, partly converted to regex format.
questions = [
    ('referee_name', r"Name of Referee\s?:?"),
    ('how_long_known', r"How long have you known? the applicant\?"),
    ('capacity_known', r"In what capacity do you know the applicant\? (?:Youth Leader and Pastor)?"),
    ('known_offences', r"""The position for which the applicant is applying requires substantial
contact with children and young people\. To the best of your knowledge,
does the applicant have any convictions/cautions/bindovers, for any
criminal offences\? Please state YES or NO:?"""),
    ('known_offences_details', r"If the answer is yes, please identify below:"),
    ('capability_children', r"""
Please comment on the applicant's capability of working with children
and young people \(i\.?e\. previous experience of similar work, sense of
responsibility, sensitivity, ability to work with others, ability to
communicate with children and young people, leadership skills\)"""),
    ('character', r"""
Please comment on aspects of the applicant'?s character \(i\.?e\. Christian
experience honesty, trustworthiness, reliability, disposition, faithful
attendance at worship/prayer meetings\.\)"""),
    ('concerns',  r"""
Have you ever had concerns about either this applicant's ability or
suitability to work with children and young people\? If you would prefer
to discuss your concerns on the telephone and in confidence, please
contact either: Colin Davies on 029 20 617391 or Shirley Evans on 020
8569 0669\."""),
    ('comments', r"Any other comments you wish to make"),
    ('_unused_1', r"Signature"),
    ('date_created', r"Date"),
]

# Replace any literal whitespace with optional whitespace matcher.
# We use this to make the questions above more readable.
def soften_whitespace(s):
    return re.sub(r"\s", r"\s+", s)

# Create the actual regex for extracting answers.
def make_regex(qs):
    return "".join([soften_whitespace(regex) + ("(?P<%s>.*)" % name) for name,regex in qs])

def parse_date(s):
    formats = [
        r"(?P<d>\d{1,2})-(?P<m>\d{1,2})-(?P<y>\d{2,4})",
        r"(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<y>\d{2,4})",
        r"(?P<d>\d{1,2})\.(?P<m>\d{1,2})\.(?P<y>\d{2,4})",
        r"(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})",
        r"(?P<y>\d{4})/(?P<m>\d{1,2})/(?P<d>\d{2,4})",
        ]
    day, month, year = None, None, None
    for f in formats:
        m = re.match(f, s)
        if m is not None:
            gs = m.groupdict()
            day, month, year = int(gs['d']), int(gs['m']), int(gs['y'])
            if len(gs['y']) == 2:
                year = year + 2000
            return datetime.date(year, month, day)
    r = re.compile(r"\s*:?\s*(?P<d>\d{1,2})(?:st|nd|rd|th)?\s+(?P<m>[a-zA-Z]*)\s+(?P<y>\d{2,4})", flags=re.IGNORECASE)
    m = r.match(s)
    if m is not None:
        gs = m.groupdict()
        day, monthname, year = int(gs['d']), gs['m'], int(gs['y'])
        if len(gs['y']) == 2:
            year = year + 2000
        # find month:
        months = {'Jan':1,
                  'Feb':2,
                  'Mar':3,
                  'Apr':4,
                  'May':5,
                  'Jun':6,
                  'Jul':7,
                  'Aug':8,
                  'Sep':9,
                  'Oct':10,
                  'Nov':11,
                  'Dec':12,
                  }
        for name, month in months.items():
            if monthname.lower().startswith(name.lower()):
                try:
                    return datetime.date(year, month, day)
                except ValueError:
                    return "*** FIXME Can't do date(%d, %d, %d) for %s ***" % (year, month, day, s)

    return "*** FIXME *** Can't parse " + s

footer_regex = re.compile("CCIW limited.*Rees", flags=re.DOTALL)

def clean(n, g):
    if n == 'how_long_known' or n == 'capacity_known':
        return g.replace("\n", " ").strip()
    elif n == 'known_offences':
        g = g.replace("_", "")
        g = g.strip()
        if g.lower().startswith("n"):
            return False
        else:
            if g.lower().startswith("y"):
                return True
            else:
                return "*** FIXME *** Can't parse " + g
    elif n == 'known_offences_details':
        # footer of page.
        return footer_regex.sub("", g).strip()
    elif n == 'date_created':
        g = g.strip().strip(".")
        return parse_date(g)
    else:
        return g.strip()

def shell(cmd):
    """
    Execute shell command and return stdout.
    If cmd is a string, it will be interpreted through the shell.
    If is it a list [commandname, arg1, arg2...], then it won't be.
    """
    return ''.join(Popen(cmd, shell=isinstance(cmd, string_types), stdout=PIPE, stderr=PIPE).stdout.readlines())

def convert_file(fname):
    ftype = shell(["file", "--brief", fname])
    if "Microsoft Office Document" in ftype:
        return shell(["antiword", fname]).replace("|"," ")
    elif "Rich Text Format" in ftype:
        return shell(["unrtf", "-t", "text", fname])
    elif "ASCII English text" in ftype or "UTF-8 Unicode English" in ftype:
        return shell(["cat", fname])
    else:
        raise Exception("Unknown file type %s" % ftype)

def scrape_file(fname):
    data = convert_file(fname)
    regex = make_regex(questions)

    m = re.search(regex, data, flags=re.DOTALL)
    if m is None:
        print("*** Could not match ***")
        for i in range(1, len(questions)+1):
            r = make_regex(questions[0:i])
            if re.search(r, data, flags=re.DOTALL) is not None:
                pass
            else:
                print("Failed on question " + questions[i-1][0])
                break
    else:
        return dict([(name, clean(name, val)) for name, val in m.groupdict().items()])




usage = """Usage:

./reference_scraper.py <filename> <application_form_id> <referee number>
"""
if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.stderr.write(usage)
        sys.exit(1)
    else:
        fname = sys.argv[1]
        data = scrape_file(fname)
        if data is None:
            sys.exit(1)
        del data['_unused_1']
        # write it out
        fd = open("reference_data.%s.%s" % (int(sys.argv[2]), int(sys.argv[3])), "w")
        fd.write(repr(data))
        fd.close()
        if "*** FIXME" in repr(data):
            sys.stderr.write("%s: there were some errors parsing:\n" % fname)
            for (k,v) in data.items():
                if isinstance(v, string_types) and "*** FIXME" in v:
                    sys.stderr.write("  " + k + "\n")
        if footer_regex.search(repr(data)) is not None:
            sys.stderr.write("Footer text is found in one of the answers.")
