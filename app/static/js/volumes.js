var populateClusterVolumes = function(cluster_id, volumes) {
  cluster_element = $("#" + cluster_id )
  if( volumes.length > 0 ){
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
  $.get( "/volumes/" + cluster_id , function( data ) {
    populateClusterVolumes(cluster_id, data)
  });
};

$( document ).ready(function() {
    console.log( "ready!" );

    var cluster_ids = $(".cluster").map(function() { return this.id; }).toArray();
    $.each( cluster_ids, function( index, cluster_id ) {
      populateClusterVolumes(cluster_id);
    });
});
