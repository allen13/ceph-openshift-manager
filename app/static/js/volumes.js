var populateClusterVolumes = function(cluster_id, data) {
  volumes = data["volumes"];
  cluster_element = $("#" + cluster_id )
  if( volumes.length >= 0 ){
    cluster_element.empty()
  }
  $.each( volumes, function( index, volume ) {
    cluster_element.append(
        "<tr><td>"
        + volume["name"]
        + "</td><td>"
        + volume["size"]
        + "</td><td>"
        + volume["project"]
        + "</td><td>"
        + volume["pv"]
        + "</td><td>"
        + volume["pvc"]
        + "</td></tr>" );
  });
};

var getClusterVolumes = function(cluster_id) {
  $.get("/volumes/" + cluster_id)
    .done(function( data ) {
      populateClusterVolumes(cluster_id, data)
    })
    .fail(function() {
      cluster_element = $("#" + cluster_id )
      cluster_element.empty()
      cluster_element.append('<tr><td colspan="5" align="center" ><i class="fa fa-exclamation" style="font-size:30px"></i></td></tr>')
    });
};

$( document ).ready(function() {
    console.log( "ready!" );

    var cluster_ids = $(".cluster").map(function() { return this.id; }).toArray();
    $.each( cluster_ids, function( index, cluster_id ) {
      getClusterVolumes(cluster_id);
    });
});
