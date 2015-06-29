DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'cciw',
        'USER': 'cciw',
        'PASSWORD': 'foo',  # Need to sync with Vagrantfile
        'HOST': 'localhost',
        'PORT': 5432,
        'CONN_MAX_AGE': 30,
        'ATOMIC_REQUESTS': True,
    }
}
