from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item

app = Flask(__name__)

engine = create_engine('sqlite:///catalog.db', connect_args={'check_same_thread': False})
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
@app.route('/catalog')
def showCatalog():
	categories = session.query(Category).all()
	items = session.query(Item).limit(10)
	return render_template('catalog.html', categories=categories, items=items)

@app.route('/category/new', methods=['GET', 'POST'])
def newCategory():
	if request.method == 'POST':
		newCategory = Category(name=request.form['name'], description=request.form['description'])
		session.add(newCategory)
		session.commit()
		return redirect(url_for('showCatalog'))
	else:
		return render_template('newcategory.html')

@app.route('/category/<int:category_id>')
def showCategory(category_id):
	category = session.query(Category).filter_by(id=category_id).one()
	items = session.query(Item).filter_by(category_id=category_id).all()
	return render_template(
		'showcategory.html', category=category, items=items)

@app.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
def editCategory(category_id):
	category = session.query(Category).filter_by(id=category_id).one()
	if request.method == 'POST':
		if request.form['name']:
			category.name = request.form['name']
		if request.form['description']:
			category.description = request.form['description']
		session.add(category)
		session.commit()
		return redirect(url_for('showCatalog'))
	else:
		return render_template(
			'editcategory.html', category=category)

@app.route('/category/<int:category_id>/delete', methods=['GET', 'POST'])
def deleteCategory(category_id):
	category = session.query(Category).filter_by(id=category_id).one()
	if request.method == 'POST':
		items = session.query(Item).filter_by(category_id=category_id).all()
		
		if items:
			for item in items:
				session.delete(item)
				session.commit()

		session.delete(category)
		session.commit()
		return redirect(url_for('showCatalog'))
	else:
		return render_template(
			'deletecategory.html', category=category)

@app.route('/category/<int:category_id>/item/new', methods=['GET', 'POST'])
def newItem(category_id):
	category = session.query(Category).filter_by(id=category_id).one()
	if request.method == 'POST':
		newItem = Item(name=request.form['name'], description=request.form['description'], 
			price=request.form['price'], category_id=category.id)
		session.add(newItem)
		session.commit()
		return redirect(url_for('showCategory', category_id=category.id))
	else:
		return render_template(
			'newitem.html', category=category)

@app.route('/category/<int:category_id>/item/<int:item_id>')
def showItem(category_id, item_id):
	category = session.query(Category).filter_by(id=category_id).one()
	item = session.query(Item).filter_by(id=item_id).one()
	return render_template(
		'showitem.html', category=category, item=item)

@app.route('/category/<int:category_id>/item/<int:item_id>/edit', methods=['GET', 'POST'])
def editItem(category_id, item_id):
	category = session.query(Category).filter_by(id=category_id).one()
	item = session.query(Item).filter_by(id=item_id).one()
	if request.method == 'POST':
		if request.form['name']:
			item.name = request.form['name']
		if request.form['description']:
			item.description = request.form['description']
		if request.form['price']:
			item.price = request.form['price']
		session.add(item)
		session.commit()
		return redirect(url_for('showCategory', category_id=category.id))
	else:
		return render_template(
			'edititem.html', category=category, item=item)

@app.route('/category/<int:category_id>/item/<int:item_id>/delete', methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
	category = session.query(Category).filter_by(id=category_id).one()
	item = session.query(Item).filter_by(id=item_id).one()
	if request.method == 'POST':
		session.delete(item)
		session.commit()
		return redirect(url_for('showCategory', category_id=category.id))
	else:
		return render_template(
			'deleteitem.html', category=category, item=item)

if __name__ == '__main__':
	app.debug = True
	app.run(host='0.0.0.0', port=5000)