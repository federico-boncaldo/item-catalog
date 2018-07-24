from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Category, Item

from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

# Read client id from clien_secrets.json
CLIENT_ID = json.loads(
	open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Application"

# Connect to Database and create a database session
engine = create_engine('sqlite:///catalog.db', connect_args={'check_same_thread': False})
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create anti-forgery state token
@app.route('/login')
def showLogin():
	state = ''.join(
		random.choice(string.ascii_uppercase + string.digits) for x in range(32))
	login_session['state'] = state
	return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
	# Validate state token
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	# Obtain authorization code
	request.get_data()
	code = request.data.decode('utf-8')

	try:
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(
			json.dumps('Failed to upgrade the authorization code'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Check that the access token is valid
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
			% access_token)

	# Submit request, parse response
	h = httplib2.Http()
	response = h.request(url, 'GET')[1]
	str_response = response.decode('utf-8')
	result = json.loads(str_response)

	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Verify that the access token is used for the intended user
	user_id = credentials.id_token['sub']
	if result['user_id'] != user_id:
		response = make_response(
			json.dumps("Token's user ID doesn't match given user ID."), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Verify that the access token is valid for this app.
	if result['issued_to'] != CLIENT_ID:
		response = make_response(
			json.dumps("Token's client ID does not match app's"), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	stored_access_token = login_session.get('access_token')
	stored_user_id = login_session.get('user_id')
	if stored_access_token is not None and user_id == stored_user_id:
		response = make_response(json.dumps('Current user is already connected.'),
								200)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Store the access token in the session for later use.
	login_session['access_token'] = access_token
	login_session['user_id'] = user_id

	# Get user info
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params=params)

	data = answer.json()

	login_session['picture'] = data['picture']
	login_session['email'] = data['email']

	# See if user exists, if it doesn't make a new one
	user_id = getUserID(login_session['email'])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	output = ''
	output += '<h1>Welcome, '
	output += login_session['email']
	output += '!</h1>'
	output += '<img src="'
	output += login_session['picture']
	output += ' " style = "width: 300px; height: 300px; border-radius: 150px; -webkit-border-radius: 150px; -mox-border-radius: 150px;">'
	flash("You are now logged in as %s" %login_session['email'])
	return output

# User Helper Functions

def createUser(login_session):
	newUser = User(email=login_session['email'], picture=login_session['picture'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email=login_session['email']).one()
	return user.id

def getUserInfo(user_id):
	user = session.query(User).filter_by(id=user_id).one()
	return user

def getUserID(email):
	try:
		user = session.query(User).filter_by(email=email).one()
		return user.id
	except:
		return None

# Disconnect - Revoke a current user's token and reset their login_session

@app.route('/gdisconnect')
def gdisconnect():
	# Only disconnect a connected user.
	access_token = login_session.get('access_token')
	if access_token is None:
		response = make_reponse(
			json.dumps('Current user not connected'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]
	if result['status'] == '200':
		# Reset the user's session.
		del login_session['access_token']
		del login_session['user_id']
		del login_session['email']
		del login_session['picture']

		flash("You have successfully been logged out.")
		return redirect(url_for('showCatalog'))
	else:
		# For whatever reason, the given token was invalid.
		flash("Failed to revoke token for given user")
		return redirect(url_for('showCatalog'))

# JSON API endpoint
@app.route('/catalog.json')
def catalogJSON():
	categories = session.query(Category).all()
	categoriesObj = {'Categories':[]}
	for category in categories:
		items = session.query(Item).filter_by(category_id=category.id).all()
		categoryObj = category.serialize
		categoryObj['Items'] = [i.serialize for i in items]
		categoriesObj['Categories'].append(categoryObj)

	return jsonify(categoriesObj)

# Show all categories and the latest 10 items
@app.route('/')
def showCatalog():
	categories = session.query(Category).all()
	items = session.query(Item).limit(10)
	return render_template('catalog.html', categories=categories, items=items)

@app.route('/category/new', methods=['GET', 'POST'])
def newCategory():
	if 'email' not in login_session:
		return redirect('/login')
	if request.method == 'POST':
		newCategory = Category(name=request.form['name'], description=request.form['description'])
		session.add(newCategory)
		session.commit()
		flash("New category created.")
		return redirect(url_for('showCatalog'))
	else:
		return render_template('newcategory.html')

@app.route('/category/<int:category_id>/<string:category_name>')
def showCategory(category_id, category_name):
	category = session.query(Category).filter_by(id=category_id).one()
	items = session.query(Item).filter_by(category_id=category_id).all()
	return render_template(
		'showcategory.html', category=category, items=items)

@app.route('/category/<int:category_id>/<string:category_name>/edit', methods=['GET', 'POST'])
def editCategory(category_id, category_name):
	if 'email' not in login_session:
		return redirect('/login')
	category = session.query(Category).filter_by(id=category_id).one()
	if request.method == 'POST':
		if request.form['name']:
			category.name = request.form['name']
		if request.form['description']:
			category.description = request.form['description']
		session.add(category)
		session.commit()
		flash("Category %s edited" %category.name)
		return redirect(url_for('showCatalog'))
	else:
		return render_template(
			'editcategory.html', category=category)

@app.route('/category/<int:category_id>/<string:category_name>/delete', methods=['GET', 'POST'])
def deleteCategory(category_id, category_name):
	if 'email' not in login_session:
		return redirect('/login')
	category = session.query(Category).filter_by(id=category_id).one()
	if request.method == 'POST':
		items = session.query(Item).filter_by(category_id=category_id).all()
		
		if items:
			for item in items:
				session.delete(item)
				session.commit()

		session.delete(category)
		session.commit()
		flash("Category %s deleted" %category.name)
		return redirect(url_for('showCatalog'))
	else:
		return render_template(
			'deletecategory.html', category=category)

@app.route('/category/<int:category_id>/<string:category_name>/item/new', methods=['GET', 'POST'])
def newItem(category_id, category_name):
	if 'email' not in login_session:
		return redirect('/login')
	category = session.query(Category).filter_by(id=category_id).one()
	if request.method == 'POST':
		newItem = Item(name=request.form['name'], description=request.form['description'], 
			price=request.form['price'], category_id=category.id)
		session.add(newItem)
		session.commit()
		flash("Category %s deleted" %category.name)
		return redirect(url_for('showCategory', category_id=category.id, category_name=category.name))
	else:
		return render_template(
			'newitem.html', category=category)

@app.route('/category/<int:category_id>/item/<int:item_id>/<string:item_name>')
def showItem(category_id, item_id, item_name):
	category = session.query(Category).filter_by(id=category_id).one()
	item = session.query(Item).filter_by(id=item_id).one()
	return render_template(
		'showitem.html', category=category, item=item)

@app.route('/category/<int:category_id>/item/<int:item_id>/<string:item_name>/edit', methods=['GET', 'POST'])
def editItem(category_id, item_id, item_name):
	if 'email' not in login_session:
		return redirect('/login')
	item = session.query(Item).filter_by(id=item_id).one()
	category = session.query(Category).filter_by(id=category_id).one()
	categories = session.query(Category).all()
	if request.method == 'POST':
		if request.form['name']:
			item.name = request.form['name']
		if request.form['description']:
			item.description = request.form['description']
		if request.form['price']:
			item.price = request.form['price']		
		if request.form['category_id']:
			item.category_id = request.form['category_id']

		categoryName = category.name
		for itemCategory in categories:
			if itemCategory.id == item.category_id:
				categoryName = itemCategory.name

		session.add(item)
		session.commit()
		flash("Item %s edited." %item.name)
		return redirect(url_for('showCategory', category_id=item.category_id, category_name=categoryName))
	else:

		return render_template(
			'edititem.html', itemCategory=category, item=item, categories=categories)

@app.route('/category/<int:category_id>/item/<int:item_id>/<string:item_name>/delete', methods=['GET', 'POST'])
def deleteItem(category_id, item_id, item_name):
	if 'email' not in login_session:
		return redirect('/login')
	category = session.query(Category).filter_by(id=category_id).one()
	item = session.query(Item).filter_by(id=item_id).one()
	if request.method == 'POST':
		session.delete(item)
		session.commit()
		flash("Item %s deleted." %item.name)
		return redirect(url_for('showCategory', category_id=category.id, category_name=category.name))
	else:
		return render_template(
			'deleteitem.html', category=category, item=item)

if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=5000)