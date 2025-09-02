# Run this with:

#   locust --config scripts/attic/bookings_load_test_2025.conf

from locust import HttpUser, task


class HelloWorldUser(HttpUser):
    def on_start(self):
        # Disable SSL verifcation, we are using certificates from staging instance of LetsEncrypt
        """on_start is called when a Locust start before any task is scheduled"""
        self.client.verify = False

    @task
    def start_page(self):
        self.client.get("/")
