"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


from app import app
import os
from unittest import TestCase
from sqlalchemy import exc
from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"


# Now we can import app


# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test user model"""

    def setUp(self):
        """Create test client, add sample data."""
        db.create_all()
        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        u1 = User.signup(
            username="testuser1",
            email="test1@test.com",
            password="HASHED_PASSWORD",
            image_url="/static/images/default-pic.png"
        )
        uid1 = 1111
        u1.id = uid1

        u2 = User(
            username="testuser2",
            email="test2@test.com",
            password="HASHED_PASSWORD",
            image_url="/static/images/default-pic.png"
        )
        uid2 = 2222
        u2.id = uid2

        db.session.add_all([u1, u2])
        db.session.commit()

        u1 = User.query.get(uid1)
        u2 = User.query.get(uid2)

        self.u1 = u1
        self.uid1 = uid1

        self.u2 = u2
        self.uid2 = uid2

        self.client = app.test_client()

    # Added teardown to cleanup after each test
    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_user_model(self):
        """Does basic model work?"""

        # u1 should have no messages & no followers
        self.assertEqual(len(self.u1.messages), 0)
        self.assertEqual(len(self.u1.followers), 0)
        self.assertEqual(
            repr(self.u1), "<User #1111: testuser1, test1@test.com>")

    def test_is_following(self):
        """Does is_following successfully detect when user1 is not following user2 and when user1 is following user2?"""

        # Test that u1 is not following u2
        self.assertFalse(self.u1.is_following(self.u2))

        # Add record to follows table for u1 to follow u2
        follow = Follows(user_being_followed_id=self.u2.id,
                         user_following_id=self.u1.id)

        db.session.add(follow)
        db.session.commit()

        # Test u1 is now following u2
        self.assertTrue(self.u1.is_following(self.u2))

    def test_is_followed_by(self):
        """"
        Does is_followed_by successfully detect when user1 is not followed by user2?

        Does is_followed_by successfully detect when user1 is followed by user2?
        """

        # Test that u2 is not followed by u1
        self.assertFalse(self.u1.is_followed_by(self.u2))

        # Add record to follows table for u2 to follow u1
        follow = Follows(user_being_followed_id=self.u1.id,
                         user_following_id=self.u2.id)

        db.session.add(follow)
        db.session.commit()

        # Test u1 is now followed by u2
        self.assertTrue(self.u1.is_followed_by(self.u2))

 ########### User Signup Tests ###########

    def test_create_valid_user(self):
        """ 
        Does User.signup successfully create a new user given valid credentials?
        """
        # create a user using signup
        User.signup(
            username="test_user",
            email="test_user@test.com",
            password="test_password",
            image_url="/static/images/default-pic.png"
        )
        # add to users db
        db.session.commit()
        # get user instance and check attributes
        valid_user = User.query.filter_by(username='test_user').first()
        self.assertIsNotNone(valid_user)
        self.assertEqual(valid_user.username, 'test_user')
        self.assertEqual(valid_user.email, 'test_user@test.com')
        self.assertNotEqual(valid_user.password, 'test_password')
        # test that password is a bcrypt string, so it should start with $2b$
        self.assertTrue(valid_user.password.startswith("$2b$"))

    def test_create_invalid_user(self):
        """ 
        Does User.signup fail to create a new user if any of the validations fail? 

        Email, username and password are not nullable (can not be empty).

        """
        with self.assertRaises(exc.IntegrityError):
            User.signup(
                username="testuser3",
                email=None,
                password="12345",
                image_url=None
            )
        # integrity error will be raised after attempting commit
            db.session.commit()

    def test_create_duplicate_user(self):
        """
        Does User.create fail to create a duplicate user if username or email already exists? 

        Username and email should be unique for each user

        """
        # Creating a user
        User.signup(
            username="testuser3",
            email="test3@test.com",
            password="12345",
            image_url="/static/images/default-pic.png"
        )

        db.session.commit()

        # Attempt to create another user with the same credentials
        with self.assertRaises(exc.IntegrityError):
            User.signup(
                username="testuser3",
                email="test3@test.com",
                password="12345",
                image_url="/static/images/default-pic.png"
            )
        # integrity error will be raised after attempting commit
            db.session.commit()

    ########### Authentication Tests  ###########

    def test_valid_authentication(self):
        """
        Does User.authenticate successfully return a user when given a valid username and password?
        """
        u = User.authenticate(self.u1.username, "HASHED_PASSWORD")
        self.assertIsNotNone(u)
        self.assertEqual(u.id, self.uid1)

    def test_invalid_username(self):
        self.assertFalse(User.authenticate("bad_username", "password"))

    def test_wrong_password(self):
        self.assertFalse(User.authenticate(self.u1.username, "wrong_password"))
