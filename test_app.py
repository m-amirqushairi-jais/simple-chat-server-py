import unittest
from flask_testing import TestCase
from app import app, db, User


class TestChatApp(TestCase):

    def create_app(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_user_registration(self):
        response = self.client.post(
            '/register', json={"username": "testuser", "password": "testpass"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"msg": "User created"})

        user = User.query.filter_by(username="testuser").first()
        self.assertIsNotNone(user)

    def test_duplicate_user_registration(self):
        response = self.client.post(
            '/register', json={"username": "testuser", "password": "testpass"})
        self.assertEqual(response.status_code, 201)
        response = self.client.post(
            '/register', json={"username": "testuser", "password": "testpass"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {"msg": "User already exists"})

    # Add more tests as needed


if __name__ == '__main__':
    unittest.main()
