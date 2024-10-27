from flask import (Flask, render_template, redirect, 
                   url_for,request, session, flash, send_file, jsonify, abort)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from functools import wraps
import datetime

from bson.json_util import dumps


import pandas as pd
import random
import os



app = Flask(__name__)

app.config['SECRET_KEY']  = os.getenv("SECRET_KEY")
app.config["MONGO_URI"] = os.getenv("MONGO_URI")


mongo = PyMongo(app)
db = mongo.db

# Decorators USER AUTHENTICATION
def login_required(f):
    @wraps(f)
    def wrap(*arg, **kwargs):
        if 'logged_in' in session:
            return f(*arg, **kwargs)
        else:
            return redirect('/')
    return wrap

# # ROUTES of the USER AUTHENTICATION
# add @login_required if needed
# jq responsible for redirecting when loggingin or signingup
import user.routes

@app.route('/', methods=('GET', 'POST'))
def welcomepage():
    return render_template('user-authentication.html')


@app.route('/home', methods=('GET', 'POST'))
@login_required
def home():
    user_id = session['user']['_id']
    decks = list(db.decks.find({"user": user_id}))
    without_decks = db[user_id].count_documents({ "decks": None })
    number_deck = [
            {
                "$lookup": {
                    "from": "decks",
                    "let": { "local_decks": { "$toObjectId": "$decks" } },
                    "pipeline": [
                        { "$match": { "$expr": { "$eq": [ "$_id", "$$local_decks" ] } } },
                        { "$project": { "name": 1, "last_stadied": 1, "created_date": 1 } }  # Include the additional fields
                    ],
                    "as": "matched_docs"
                }
            },
            {
                "$unwind": "$matched_docs"  # Unwind the matched_docs array to de-normalize
            },
            {
                "$group": {
                    "_id": { "deck_id": "$decks", "name": "$matched_docs.name", "last_stadied": "$matched_docs.last_stadied", "created_date": "$matched_docs.created_date" },  # Group by deck_id, name, and additional fields
                    "count": { "$sum": 1 }  # Count the number of terms
                }
            },
            {
                "$project": {
                    "_id": { "$toObjectId": "$_id.deck_id" },  # Convert deck_id back to ObjectId
                    "name": "$_id.name",
                    "last_stadied": "$_id.last_stadied",
                    "created_date": "$_id.created_date",
                    "count": 1
                }
            }
        ]
    # counts number of terms per deck
    number_deck = list(db[user_id].aggregate(number_deck))
    
    # merges number_deck & decks into one list
    ids_decks = [deck['_id'] for deck in decks]
    ids_num_deck =  [deck['_id'] for deck in number_deck]
    decks = {deck['_id']:deck for deck in decks}
    # if there are decks without terms then add them to number_deck list and add to those objects count = 0
    if len(ids_decks) != len(ids_num_deck):
        for id in ids_decks:
            if id not in ids_num_deck:
                decks[id]['count'] = 0
                number_deck.append(decks[id])

    # sort number_deck
    number_deck = sorted(number_deck, key=lambda x: x["created_date"], reverse=False) 

    
    return render_template('home.html', decks = number_deck, without_decks=without_decks)



@app.route('/deck-menu/<id>')
@login_required
def deck_menu(id):
    user_id = session['user']['_id']
    deck = db.decks.find_one({"_id": ObjectId(id)})
    words = db[user_id].find({"decks": id})

    return render_template('deck-menu.html', words=words, deck=deck)



@app.route('/new-deck', methods=('GET', 'POST'))
@login_required
def new_deck():
    user_id = session['user']['_id']
    if request.method == 'POST':
        deck_name = request.form['name']
        # gives back ID of a new deck
        id = db.decks.insert_one({'name': deck_name, 
                                  'created_date': datetime.datetime.now(), 
                                  'user': user_id, 
                                  'last_stadied':datetime.datetime.now()})


        return redirect(url_for('deck_menu',id=str(id.inserted_id)))

    return render_template('new-deck.html')



@app.post("/<id>/delete/")
@login_required
def delete_deck(id):
    '''
    - delete decks
    - removes deck id from words and makes them unasigned 
    '''
    user_id = session['user']['_id']
    db.decks.delete_one({"_id":ObjectId(id)})
    db[user_id].update_many(
        {'decks': id},
        {'$set': {'decks': None}}
    )

    return redirect(url_for('home'))




@app.post('/<id>/delete-term/<term_id>')
@login_required
def delete_term(id, term_id):
    user_id = session['user']['_id']
    db[user_id].delete_one({"_id":ObjectId(term_id)})
    return redirect(url_for('deck_menu',id=id))


@app.route('/<id>/update-term/<term_id>', methods=('GET', 'POST'))
@login_required
def update_term(id, term_id):
    user_id = session['user']['_id']
    existing_term = db[user_id].find_one({"_id": ObjectId(term_id)})

    if request.method == 'POST':
        new_term = request.form.get('term')
        new_definition = request.form.get('definition')
        db[user_id].update_one(
                {"_id": ObjectId(term_id)},
                {"$set": {
                    'term': new_term,
                    'definition': new_definition,
                    'added':existing_term['added'],
                    'decks': id,
                    'to_be_repeated': False
                }}
            )
        return redirect(url_for('deck_menu',id=id))
    
    return render_template('update-term.html', existing_term=existing_term,id=id)


@app.route('/update-term-deck/<term_id>', methods=('GET', 'POST'))
@login_required
def update_term_deck(term_id):
    """USED TO REASSIGN DECKS IN display-terms.html - dropdown list"""
    user_id = session['user']['_id']
    if request.method == 'POST':
        data = request.json
        if not data or 'deck_id' not in data:
            return jsonify({'error': 'Invalid data format'}), 400
        
        deck_id = data.get('deck_id')
        if not deck_id:
            return jsonify({'error': 'Invalid deck ID'}), 400
        try:
            result = db[user_id].update_one(
                {"_id": ObjectId(term_id)},
                {"$set": {
                    'decks': deck_id
                }}
            )
        except Exception as e:
            print(e)
            return jsonify({'error': 'Failed to update term deck'}), 500

        if result.modified_count == 0:
            return jsonify({'error': 'Term not found'}), 404

        return jsonify({'message': 'Update succeeded'}), 200
    else:
        return abort(405)
    


@app.route('/update-term-status/<term_id>', methods=('GET', 'POST'))
@login_required
def update_term_status(term_id):
    """USED TO REASSIGN TERM'S STATUS"""
    user_id = session['user']['_id']
    if request.method == 'POST':
        data = request.json
        if not data or 'new_status' not in data:
            return jsonify({'error': 'Invalid Term Status(TRUE/FALSE) format'}), 400
        
        new_status = data.get('new_status')

        if not new_status:
            return jsonify({'error': 'Invalid Term Status(TRUE/FALSE) '}), 400
        try:
            new_status = True if new_status == "True" else False
            result = db[user_id].update_one(
                {"_id": ObjectId(term_id)},
                {"$set": {
                    'to_be_repeted': new_status
                }}
            )
        except Exception as e:
            print(e)
            return jsonify({'error': 'Failed to update tTerm Status(TRUE/FALSE)'}), 500

        if result.modified_count == 0:
            return jsonify({'error': 'Term not found'}), 404

        return jsonify({'message': 'Update of Term Status(TRUE/FALSE) succeeded'}), 200
    else:
        return abort(405)


@app.route('/deck/<id>/new-term', methods=('GET', 'POST'))
@login_required
def add_new_term(id):
    user_id = session['user']['_id']
    if request.method == 'POST':
        term = request.form['term']
        definition = request.form['definition']
        db[user_id].insert_one({'term': term, 
                             'definition': definition ,
                             'added': datetime.datetime.now(), 
                             'decks': id, 'to_be_repeted': False
                             })

        return redirect(url_for('deck_menu',id=id))
    
    return render_template('new-term.html', id=id)


@app.route('/upload-data/<deck_id>/<deck_name>',methods=("POST", "GET"))
@login_required
def upload_data(deck_id, deck_name ):

    user_id = session['user']['_id']

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Something has gone wrong. The file was not uploaded. Please try again.')
            return redirect(request.url)
        
        file = request.files['file']

        if file.filename == '':
            flash('File not provided.')
            return redirect(request.url)
        
        if file:
            # Read CSV file into a pandas DataFrame
            df = pd.read_csv(file,index_col=False)
            df['added'] = datetime.datetime.now()
            df['decks'] = deck_id
            df['to_be_repeted'] = False

            records = df.to_dict(orient='records')
            db[user_id].insert_many(records)

            return redirect(url_for('deck_menu',id=deck_id))
    
    return render_template('uploader.html', deck_id=deck_id, deck_name=deck_name)


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(500)
def error_handler(error):
    """
    500 is Internal Server Error however some of the erorrs might have no an HTTP status code then 500 will be used
    """
    error_code = getattr(error, 'code', 500)
    
    return render_template('error.html', error_code=error_code), error_code


def clean_words(words):
    # converting _id to string & cleaning the data
    updated_words = list()
    for word in words:
        data = {
            '_id': str(word['_id']),
            'term': word['term'],
            'definition': word['definition'],
            'to_be_repeted': word['to_be_repeted'],
            'added': word['added']
        }
        updated_words.append(data)
    return updated_words


def sort_words(updated_words, term_definition, sort,repeat, first ):
    """used to sort words used in views: study, display terms"""
    if term_definition != 'term_first':
        first = 'definition'
    if sort == 'ASC_ALP':
        updated_words = sorted(updated_words, key=lambda x: x[first])
    elif sort == 'DESC_ALP':
        updated_words = sorted(updated_words, key=lambda x: x[first], reverse=True)
    elif sort == 'ADDED_ASC':
        updated_words.sort(key=lambda item:item['added'])
    elif sort == 'ADDED_DESC':
        updated_words.sort(key=lambda item:item['added'], reverse= True)
    elif sort == 'SHUFFLE':
        random.shuffle(updated_words)

    if repeat != 'REPEAT_ALL':
        updated_words = [item for item in updated_words if item['to_be_repeted']]

    return first, updated_words


@app.route('/all-terms', methods=('GET', 'POST'))
@login_required
def display_terms():
    user_id = session['user']['_id']
    sort= "ADDED_ASC"
    decks = db.decks.find({'user': user_id})
    decks = {str(deck['_id']): deck['name'] for deck in decks} # converts _id to string witout it we would get json.dump() gives me "TypeError: keys must be a string" in <script>
    terms = db[user_id].find({})
    updated_terms = []
    for term in terms:
        if term['decks'] == None:
            term['decks_name'] = None
        else:
            term['decks_name'] = decks[term['decks']]
        updated_terms.append(term)

    if request.method == 'POST':
        sort = request.form.get('data-state')
        _, updated_terms = sort_words(updated_terms, 'term_first', sort,'REPEAT_ALL', 'term' )
        print(sort,updated_terms[0])
        return render_template('display-terms.html', terms=updated_terms, decks=decks, sort=sort)

    return render_template('display-terms.html', terms=updated_terms, decks=decks, sort=sort)



@app.route('/study/<deck_id>', methods=('GET', 'POST'))
@login_required
def study(deck_id):
    """this is study flashcards for deck words"""

    user_id = session['user']['_id']
    updated_words = list()
    show_study_menu = True
    first = 'term'

    try:
        print(deck_id)
        if deck_id == "none":
            words = db[user_id].find({})
        else:
            words = list(db[user_id].find({"decks": deck_id}))
        # converting _id to string & cleaning the data 
        updated_words = clean_words(words)
        
    except Exception as e:
        print(f"An error occurred while fetching words: {e}")
        abort(500)

    if request.method == 'POST':
        show_study_menu = False
        term_definition = request.form['term_definition']
        sort = request.form['sort']
        repeat = request.form['repeat']

        # update study time
        if deck_id != "none":
            db.decks.update_one(
                    {"_id": ObjectId(deck_id)},
                    {"$set": {
                        'last_stadied': datetime.datetime.now()
                    }})

        first, updated_words = sort_words(updated_words, term_definition, sort,repeat, first )

        

    # Pass the serialized words data to the template
    return render_template('study.html', words=updated_words, 
                           deck_id=deck_id, 
                           show_study_menu=show_study_menu, 
                           first=first)



if __name__ == '__main__':
    app.run(debug=True)

