from app import application
from flask import render_template, flash, redirect, url_for
from app.forms import LoginForm, RegistrationForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from werkzeug.urls import url_parse
from app import db
from flask import request 
from flask_socketio import emit
from app import socketio
import random
import pymongo
from app.serverlibrary import TicTacToe, Move, mergesort

########################
# Setup for global data
#######################
# Paste in your connection string for MongoDB
# replace the None with the string for connection
client = pymongo.MongoClient(None)

# Connect to test database
dbmongo = client.test

marks = ('X', 'O')
players = {}

#############################################
# Put any other helper functions you use here
#############################################


def calculate_score(winning, draw):
    return winning * 10 + draw * 5

def update_score(user, status):
    if status == 'win':
        if current_user.winning == None:
            current_user.winning = 1
        else:
            current_user.winning += 1
    elif status == 'draw':
        if current_user.draw == None:
            current_user.draw = 1
        else:
            current_user.draw += 1
    score = calculate_score(current_user.winning, current_user.draw)
    current_user.score = score
    db.session.commit()

#######################################
# These are event handler for SocketIO
######################################

################
# Exercise 6
###############

########
# Task 1
########
@socketio.on('startconnect', namespace='/tictactoe')
def handle_connect(message):
    print("Connected")
    mark = message["mark"]
    collection = dbmongo[current_user.username]
    if collection.count_documents({}) < 1:
        collection.insert_one({'cell': [['_', '_', '_'], 
                                        ['_', '_', '_'],
                                        ['_', '_', '_']],
                               'mark': mark})
    last_data = collection.find().limit(1).sort([('_id',-1)])[0]
    players[current_user.username] = TicTacToe(last_data['cell'],
                                           last_data['mark'])
    emit('afterconnect', {'data': last_data['cell']})
    
##########
# Task 2
##########
@socketio.on('clicked', namespace='/tictactoe')
def handle_click(message):
    # get the user name, mark and the clicked cell from message
    # check clientlibrary.py for the message sent in 
    # event 'clicked'
    # replace the None
    user = message[None]
    mark = message[None]
    
    # set the computer mark to be the opposite of that of player
    computer = None
    
    # get the cell number from 'id' inside message
    # Note that the format for the cell string is 'cellXY'
    # extract only the last two characters
    cell = None
    
    #collection = dbmongo.get_collection(user)
    # get the collection from dbmongo database, replace the None
    collection = dbmongo[user]
    
    # update TicTacToe's object using the mark at the approriate row and col
    # replace the None
    players[user].update(None, None, None)
    
    # check if there is any winner
    # you can call checkwinning method inside TicTacToe's object
    winner = None
    
    # if there is a winner
    if winner != None:
        # process the winning state, and update the score
        process_winning(user, mark, collection, 
                        winner, status='win')
        
        # exit the function
        return

    # if there is no winner, check if there is any move lefts
    # get the boolean value by calling a method inside TicTacToe
    can_move = None
    # if the computer can make a move
    if can_move:
        # find the best move for the computer
        next_move = players[user].find_best_move(computer)
        
        # update the board with the best move
        # replace the None
        players[user].update(None, None, None)
        
        # check if there is a winner
        # call a method inside TicTacToe
        winner = None
        
        # emit signal 'computer_move' to update the page
        emit('computer_move', {'data': {'row':next_move.row, 'col':next_move.col}})
        
        # insert a new document to MongoDB on the board's status
        collection.insert_one({'cell':players[user].board,
                               'mark': mark})

        # check if there is a winner
        if winner != None:
            # process winning state, 
            # but do not update the score since computer wins
            process_winning(user, mark, collection,
                            winner, status='lose')
            
            # exit the function
            return

    else:
        # if there is no winner
        # update the score as draw
        process_winning(user, mark, collection,
                        winner=None, status='draw')
        return

#######################
# Flask route handlers
######################

#####################
# Exercise 5
####################

#########
# Task 3
#########
@application.route('/single', methods=['GET', 'POST'])
@login_required
def single():
    user = current_user.username
    if request.method == 'POST':
        # get collection from dbmongo database using the username
        # replace None 
        collection = dbmongo[None]
        
        # reset the tictactoe board to the original state
        # the TicTacToe's object is stored in players[user] variable
        players[user].reset()
        
        # get the mark for the current player
        # replace None
        player_mark = None
        
        # get the mark for the computer player
        # replace None with your code
        computer_mark = None
        
        # update dbmongo collection
        # the 'cell' should be the state of the board
        #  which can be obtained from the tictactoe object
        # the 'mark' should be the player's mark
        # replace None
        data = {'cell': None, 'mark': None}
        collection.insert_one(None)
        return render_template('single.html', title='Single Player', player=player_mark, computer=computer_mark)
    else:
        if user not in players:
            # set player mark randomly
            player_mark = random.choice(marks)
            
            # set the computer mark
            # replace None with your code
            computer_mark = None
        else:
            # if user is already in the dictionary, use the mark there
            # the TicTacToe object is stored inside players[user] variable
            player_mark = players[user].mark
            
            # set the computer mark
            # replace None with your code
            computer_mark = None
        return render_template('single.html', title='Single Player', player=player_mark, computer=computer_mark)


@application.route('/records')
def records():
    users = User.query.order_by(User.score).all()[::-1]
    return render_template('records.html', title="Your Records", records=users
)


@application.route('/users')
@login_required
def users():
    users = User.query.all()
    mergesort(users, lambda item: item.username)
    usernames = [u.username for u in users]
    return render_template('users.html', title='Users',
           users=usernames)

@application.route('/')
@application.route('/index')
@login_required
def index():
    return render_template('index.html', title='Home')

@application.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@application.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@application.route('/register', methods=['GET', 'POST'])
def register():
        if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user.')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

