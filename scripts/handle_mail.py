#!/usr/bin/env python2.4
import _cciw_env

def main():
    # TODO: error handling
    from cciw.mail.lists import handle_all_mail
    handle_all_mail()

if __name__ == '__main__':
    main()
