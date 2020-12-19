$(document).ready(function(){
	var apigClient = apigClientFactory.newClient();

	var getUrlParameter = function getUrlParameter(sParam) {
	    var sPageURL = window.location.search.substring(1),
	        sURLVariables = sPageURL.split('&'),
	        sParameterName,
	        i;

	    for (i = 0; i < sURLVariables.length; i++) {
	        sParameterName = sURLVariables[i].split('=');

	        if (sParameterName[0] === sParam) {
	            return sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
	        }
	    }
	}

	$('.center').prepend('<img class="resize" src="images/unauthorized/' + getUrlParameter('faceID') + '.jpg">')

	function authorizeNewUserPost(name, phone_number) {
	    // params, body, additionalParams
	    console.log("hey")
	    return apigClient.authorizeNewUserPost({}, {
	      "name": name,
	      "phone_number": phone_number,
	      "faceID": getUrlParameter('faceID')
	    }, {});
	 }

	$("#visitor-info-submit").click(function(){	
		console.log("start")
		name=$("#visitor-name").val()
		console.log(name)
		phone_number = $("#phone-number").val()
		console.log(phone_number)
		authorizeNewUserPost(name, phone_number)
		console.log(getUrlParameter('faceID'))
	})
});