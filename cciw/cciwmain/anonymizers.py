import mailer.models as mailer_models

from anonymizer import Anonymizer

class MessageLogAnonymizer(Anonymizer):

    model = mailer_models.MessageLog

    attributes = [
         # Skipping field id
        ('message_data', "similar_lorem"),
        #('when_added', "datetime"),
        #('priority', "choice"),
        #('when_attempted', "datetime"),
        #('result', "choice"),
        ('log_message', "lorem"),
    ]
