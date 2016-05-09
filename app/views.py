from flask import render_template, flash, redirect
from app import app
from .forms import LoginForm
from volumes import get_ceph_openshift_volumes

@app.route('/')
@app.route('/index')
def index():
    page_data = dict()
    page_data['rbd_images'] = get_ceph_openshift_volumes()

    if request.mimetype == 'application/json':
        return jsonify(page_data)
    else:
        return render_template('volumes.html', data=page_data, config=get_ceph_clusters())


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for OpenID="%s", remember_me=%s' %
              (form.openid.data, str(form.remember_me.data)))
        return redirect('/index')
    return render_template('login.html',
                           title='Sign In',
                           form=form,
                           providers=app.config['OPENID_PROVIDERS'])
