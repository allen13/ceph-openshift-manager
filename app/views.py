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

    return render_template(
        'volumes.html',
        ceph_clusters=get_ceph_clusters().keys(),
        projects=get_openshift_projects(),
        form=form
    )


@app.route('/volumes/<cluster>', methods=['GET'])
def get_cluster_volumes(cluster):
    volumes = get_cluster_ceph_openshift_volumes(cluster)
    return jsonify({"volumes": volumes})
