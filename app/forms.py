from flask.ext.wtf import Form
from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired


class VolumeForm(Form):
    volumeName = StringField('volumeName', validators=[DataRequired()])
    volumeSize = IntegerField('volumeSize', validators=[DataRequired()])
    cluster = StringField('cluster', validators=[DataRequired()])
    project = StringField('project', validators=[DataRequired()])
