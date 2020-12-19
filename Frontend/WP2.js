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

	function allowAccessPost(otp) {
	    // params, body, additionalParams
	    console.log("hey")
	    return apigClient.allowAccessPost({}, {
	      "otp": otp,
	      "faceID": getUrlParameter('faceID')
	    }, {});
	 }

	$("#otp-submit").click(function(){	
		console.log("start")
		otp=$("#otp").val()
		var yo = allowAccessPost(otp)
		console.log(yo)
		yo.then(
		  function(data) {
		    /* process the data */
		    if (data.data.statusCode === 200){
		    	$(".center").css({"border": "1px solid black"});
			    $('#lol').empty()
			    name= data.data.body.name
				var welcome = "<div class='text-center'><div class='pushed'>WELCOME, " + name + "</div></div>"
				$('#lol').append(welcome)
		    }else{
		    	$('#error').empty()
		    	$('#error').append("Wrong OTP, try again please.")
		    	$(".center").css({"border": "1px solid red"});
		    }
		    console.log(data.data.statusCode)
		  },
		  function(error) {
		    /* handle the error */
		    console.log("something is going wrong")
		  }
		);
	})
});