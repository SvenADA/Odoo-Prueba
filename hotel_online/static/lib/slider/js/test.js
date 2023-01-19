$(document).ready(function () {
	setTimeout(function () {
		console.log("Light Slider");
		$('.image-gallery-cls').lightSlider({
			gallery: true,
			item: 1,
			thumbItem: 4,
			slideMargin: 0,
			speed: 500,
			auto: true,
			loop: true,
			onSliderLoad: function () {
				$('.image-gallery-cls').removeClass('cS-hidden');
			}

		});
	}, 1000);

	$("#room_form").submit(function (e) {

		var myform = document.getElementById('room_form');
		var inputTags = myform.getElementsByTagName('input');
		var select = myform.getElementsByTagName('select');

		var checkboxCount = 0;
		var flag = false;
		var select_adult = false;
		var select_NoOfRooms=false;

		for (var i = 0, length = inputTags.length; i < length; i++) {
//			console.log("inputTags[i].type:::::::::::::", inputTags[i].type)
			if (inputTags[i].type == 'checkbox') {
				var cb = $(inputTags[i]);
                console.log('------------ ,', cb.is(':checked'));
				if (cb.is(':checked')) {
                    var selectEl = $("select[name='adult_"+cb.attr('id')+"']");
				    var selectNoOfRooms = $("select[name='no_room_"+cb.attr('id')+"']");
				    if (parseInt(selectEl.find(':selected').val()) == 0) {
                        select_adult = true;
                    }
                    if(parseInt(selectNoOfRooms.find(':selected').val()) == 0){
                        select_NoOfRooms = true
                    }
				    flag = true;
				}else{
				    var selectEl = $("select[name='adult_"+cb.attr('id')+"']");
				    var selectNoOfRooms = $("select[name='no_room_"+cb.attr('id')+"']");
				    console.log('------------ ,',parseInt(selectEl.find(':selected').val()),selectNoOfRooms.find(':selected').val(), cb.is(':checked'));
				    if ((parseInt(selectEl.find(':selected').val()) > 0) || (parseInt(selectNoOfRooms.find(':selected').val()) > 0)) {
                        cb.attr('checked',true);
                    }
				}
				checkboxCount++;
			}
		}

        if(select_NoOfRooms == true){
            alert('Please Select Atleast One room!');
		    return false;
        }

        if(select_adult == true){
		    alert('Please Select Atleast One adult!');
		    return false;
        }

		if (flag == false) {
			alert("Please Select Atleast One Room!");
			e.preventDefault();

		}
	});
});

function onchange_tax(val) {
	tot = parseFloat($("#total").val()) + parseFloat($("#tax").val())
	$("#grand_total").val(tot)
}
