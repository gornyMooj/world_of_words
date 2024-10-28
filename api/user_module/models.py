from flask import Flask, jsonify, request, session, redirect
from passlib.hash import pbkdf2_sha256
from bson.objectid import ObjectId

from ..basic import db

class User:

    def start_session(self, user):
        # seleting password before saving it to session
        del user['password']
        session['logged_in'] = True
        session['user'] = user
        return jsonify(user), 200

    def signup(self):
        # Create the user
        user = {
            "name": request.form.get('name'),
            "email": request.form.get('email'),
            "password": request.form.get('password'),
        }

        # Encrypt the password
        user['password'] = pbkdf2_sha256.encrypt(user['password'])

        # Check for the existing email address
        if db.users.find_one({"email": user['email']}):
            return jsonify({"error": "Email address already in use"}), 400

        # Insert the user into the database
        result = db.users.insert_one(user)
        user['_id'] = str(result.inserted_id)  # Get the inserted ID
        
        return self.start_session(user)  # Start session and respond
        
    
    def signout(self):
        session.clear()
        return redirect('/')
    
    def login(self):
        user = db.users.find_one({"email": request.form.get('email')})

        if user and pbkdf2_sha256.verify(request.form.get('password'), user['password']):
            # Add the inserted ID to the user object and convert it to a string
            user['_id'] = str(user['_id'])
            return self.start_session(user)
        
        return jsonify({"error": "Invalid login credentials"}), 401