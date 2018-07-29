from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

class CategoryForm(FlaskForm):
	name = StringField('name', validators=[DataRequired()])

class ItemForm(FlaskForm):
	name = StringField('name', validators=[DataRequired()])