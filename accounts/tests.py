from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()


class AuthAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_returns_tokens(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "john",
                "email": "john@example.com",
                "password": "secret",
                "confirm_password": "secret",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "john",
                "email": "john@example.com",
                "password": "a",
                "confirm_password": "b",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class RegistrationResponseTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_returns_json_tokens(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "pass123",
                "confirm_password": "pass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["username"], "newuser")
