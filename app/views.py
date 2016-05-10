from flask import render_template, flash, redirect, request, jsonify
from app import app
from forms import *
from volumes import *

@app.route('/', methods=['GET'])
@app.route('/volumes', methods=['GET', 'POST'])
def index():
    form = VolumeForm()
    if form.validate_on_submit():
        create_ceph_openshift_volume(
            form.cluster.data,
            str(form.volumeName.data),
            form.volumeSize.data,
            form.project.data
        )
        return redirect('/volumes')

    page_data = dict()
    page_data['rbd_images'] = get_ceph_openshift_volumes()

    if request.mimetype == 'application/json':
        return jsonify(page_data)
    else:
        return render_template(
            'volumes.html',
            ceph_clusters=get_ceph_clusters().keys(),
            projects=get_openshift_projects(),
            form=form
        )

@app.route('/volumes/<cluster>', methods=['GET'])
def get_cluster_volumes(cluster):
    return jsonify(get_cluster_ceph_openshift_volumes(cluster))
