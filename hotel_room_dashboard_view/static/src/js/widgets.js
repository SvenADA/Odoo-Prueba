odoo.define('hotel_room_dashboard_view', function(require) {
	'use strict';
//	alert("LOad");
	var core = require('web.core');
	var AbstractAction = require('web.AbstractAction');
	var Widget = require('web.Widget');
//	var Models = require('web.Model');
	var webclient = require('web.WebClient');
//	var Model = require('web.DataModel');
	var datepicker = require('web.datepicker');
	var time = require('web.time');
	var framework = require('web.framework');
	var session = require('web.session');
	var _t = core._t;
	var _lt = core._lt;
	var QWeb = core.qweb;
	var Class = core.Class;
	var RoomDashboardView = AbstractAction.extend({
		template : 'RoomDashboardView',
		init : function(parent, options) {
			console.log("INit ")
			this._super(parent,options);
			options = options || {};
			var self = this;
			this.reservation_lines = null;
			this.reservations = null;
			this.booking_data = new Array();
			this.categories;
			this.product_lines;
			this.product_template_lines;
			this.selected_categ = new Array();
			this.guest_details = new Array();
			this.housekeeping_lines = new Array();
			this.view_ids;
		},
		show : function() {
			this.$el.show();
		},

		start : function() {
			var self = this;
			self.renderElement();

			this.$(".openerp.oe_application > div").addClass('custom_oe_application');

			this.$("#from_date").datepicker({
				showButtonPanel : true,
				dateFormat : "yy-mm-dd",
				changeMonth : true,
				changeYear : true,
				altField : "#alternate",
			});

			jQuery.datepicker._gotoToday = function(id) {
				var today = new Date();
				var dateRef = jQuery("<td><a>" + today.getDate() + "</a></td>");
				this._selectDay(id, today.getMonth(), today.getFullYear(), dateRef);
			};

			this.$("#to_date").datepicker({
				showButtonPanel : true,
				dateFormat : "yy-mm-dd",
				changeMonth : true,
				changeYear : true,

			});
			this.$("#show_dashboard").click(function() {
				self.show_dashboard();
			});

			this.$("#close_button").click(function() {
				framework.unblockUI();
				window.location = '/web';
			});

			self.fetch('product.category', ['id', 'name', 'isroomtype', 'parent_id', 'child_id'], [['isroomtype', '=', true],['company_id','=',session.company_id]], {}).then(function(room_type) {
				for (var i = 0; i < room_type.length; i++) {
					$("#room_type").append($("<option>", {
						text : room_type[i].name,
						value : room_type[i].id
					}));
				}
				self.categories = room_type;
			});

			this.$(document).tooltip({

				using : function() {
					return '<div style="color:red;">' + this.title + '</div>';
				},

				show : {
					effect : "slideDown",
					delay : 500
				},

				hide : {
					effect : "slideUp",
					delay : 100
				},

			});

			self.fetch('sale.shop', ['id', 'name'], [], {}).then(function(shop) {
				for (var i = 0; i < shop.length; i++) {
					$("#shops").append($("<option>", {
						text : shop[i].name,
						value : shop[i].id
					}));
				}

			});
		},

		renderElement : function() {
			this._super();
		},

		show_dashboard : function() {
			$("#powered_by").hide();
			$("#tbl_dashboard").html("");
			var self = this;
			var room_type=$("#room_type").val()
			if (room_type == null) {
				alert("Please Add room type");
				return false
				}
			if ($("#from_date").val() == "") {
				alert("Please Enter From Date");
				return true;
			} else if ($("#to_date").val() == "") {
				alert("Please Enter To Date");
				return true;
			}



			self.from_date = time.str_to_date($("#from_date").val());
			self.to_date = time.str_to_date($("#to_date").val());
			self.next_date = self.from_date;
			var th = '<th width="100px" height="27px">Room No</th><th width="200px"><div class="extra_div"></div></th>';
			var td;
			var tdmonths = '<td  width="200px" ><div class="extra_div"></div></td>';
			if (self.from_date > self.to_date) {
				alert("To Date must be greater than From Date");
				return true;
			}
			$.when(this.load_data()).then(function() {
				self.selected_categ = new Array();
				self.fetch('product.category', ['id', 'name'], [['id', 'child_of', [parseInt($("#room_type").val())]]], {}).then(function(child_ids) {
//					console.log("ccccccccccccccccccccccc",child_ids)
					if (child_ids.length > 0) {
						for (var ch = 0; ch < child_ids.length; ch++) {
							self.selected_categ.push(child_ids[ch].id);
						}
					}

					//*****************Creating Table headers**********************************
					var cnt = 0;
					while (self.next_date <= self.to_date) {
						var prev_date = new Date(self.next_date);
						prev_date.setDate(prev_date.getDate() - 1);
						if (self.next_date.toDateString().substr(0, 3) == "Sat" || self.next_date.toDateString().substr(0, 3) == "Sun") {
							th = th + "<th style='color:red;'>" + self.next_date.toDateString().substr(0, 3) + "<br/>" + self.next_date.getDate() + "</th>";
						} else {
							th = th + "<th>" + self.next_date.toDateString().substr(0, 3) + "<br/>" + self.next_date.getDate() + "</th>";
						}
						if (self.next_date.getMonth() > prev_date.getMonth() || cnt == 0) {
							tdmonths = tdmonths + "<td>" + self.next_date.toDateString().substr(4, 4) + "</td>";
						} else {
							tdmonths = tdmonths + "<td></td>";
						}
						self.next_date.setDate(self.next_date.getDate() + 1);
						cnt++;
					}
					$("#tbl_dashboard").append("<tr>" + "<td>Months</td>" + tdmonths + "</tr>");
					$("#tbl_dashboard").append("<tr>" + th + "</tr>");
					self.next_date.setDate(self.next_date.getDate() - cnt);
					//*****************End of Creating Table headers**********************************
					
					//*****************Adding Room Names**********************************************

					self.fetch('hotel.room', ['id', 'categ_id', 'product_id'], [['shop_id', '=', parseInt($('#shops').val())]], {}).then(function(room) {
						for (var i = 0; i < room.length; i++) {
							td = '<td width="200px"><div class="extra_div"></div></td>';
							var count = 0;
							while (self.next_date <= self.to_date) {
//								var prod = self.get_product_list(room[i].product_id);
								var prod = room[i].product_id[1];
								var is_dirty_room = self.get_dirty_room(time.date_to_str(self.next_date), room[i].product_id);
								if (is_dirty_room == true) {
									td = td + '<td>' + '<div class="room_dirty" title="Unavailable/ Under Maintenance" id="' + prod + '_' + time.date_to_str(self.next_date) + '">**********</div></td>';
								} else {
									td = td + '<td>' + '<div class="room_available" title="Available" id="' + prod + '_' + time.date_to_str(self.next_date) + '">**********</div></td>';
								}
								self.next_date.setDate(self.next_date.getDate() + 1);
								count++;
							}
							
							self.next_date.setDate(self.next_date.getDate() - count);
							if (self.selected_categ.indexOf(room[i].categ_id[0]) >= 0) {
								$("#tbl_dashboard").append('<tr id="' + prod + '">' + prod + '<td>' + prod + '</td>' + td + '</tr>');
							}
						}//for end
						if (self.reservations != null) {
							
							for (var res = 0; res < self.reservations.length; res++) {
//							    console.log("vvvvvvvvvvvvvvvvvvvvvvv",self.reservations.length)

								var res_lines = self.reservations[res].reservation_line;
								var rline = 0;
								if (res_lines != null) {

									for ( rline = 0; rline < res_lines.length; rline++) {
										var line_info = self.get_reservation_line(res_lines[rline]);
										if (line_info != undefined) {
											if (self.selected_categ.indexOf(line_info.categ_id[0]) >= 0) {
												var n_date = time.str_to_date(line_info.checkin.substr(0, 10));
												var days = parseInt(line_info.number_of_days);
												var cnt = 0;
												var divid;
												while (cnt <= days) {
													divid = line_info.room_number[1] + "_" + time.date_to_str(n_date);
													n_date.setDate(n_date.getDate() + 1);

//													console.log("divid:::::::::::::::::::@@@@@",divid)

													$("div[id='" + divid + "']").html(self.reservations[res].reservation_no);
													$("div[id='" + divid + "']").removeClass('room_available');
													$("div[id='" + divid + "']").addClass('room_booked');
													console.log("trickyyyyyyyyyyyyyyyyyyyyyyyyy",$("div[id='" + divid + "']").hasClass("room_dirty"))
													if ($("div[id='" + divid + "']").hasClass("room_dirty")) {

														$("div[id='" + divid + "']").removeClass('room_available');
														$("div[id='" + divid + "']").addClass('room_booked_and_dirty');
													}
													$("div[id='" + divid + "']").addClass(self.reservations[res].state);
													var guests;
													if (res_lines.id_line_ids != undefined) {
														guests = self.get_guest_details(res_lines);
													} else {
														guests = false;
													}

													var tooltip_text = "<table class='tooltip_table'><tr>" 
													 + "<td >" + "Reservation No :" + "</td><td>" + self.reservations[res].reservation_no + "</td></tr>"
													 + "<tr><td>" + "Checkin Date :" + "</td><td>" + time.str_to_datetime(line_info.checkin).toString() + "</td></tr>" 
													 + "<tr><td>" + "Checkout Date :" + "</td><td>" + time.str_to_datetime(line_info.checkout).toString() + "</td></tr>" 
													 + "<tr><td>" + "Customer :" + "</td><td>" + self.reservations[res].partner_id[1] + "</td></tr>"
													 + "<tr><td>" + "Status :" + "</td><td>" + self.reservations[res].state + "</td></tr>";

													if (guests != false) {
														tooltip_text += "<tr><td>" + "Guest Details :" + "</td><td></td></tr>" + "<tr><td colspan='2'>" + guests + "</td></tr>" + "</table>";
													} else {
														tooltip_text += "</table>";
													}
													if ($("div[id='" + divid + "']").length > 0) {
														if ($("div[id='"+ divid +"']")[0].title == "Available") {
															$("div[id='"+ divid +"']")[0].title = "";
														}
														$("div[id='"+ divid +"']")[0].title += $(tooltip_text).html();
													}

													if (cnt == 0) {
														$("div[id='" + divid + "']").addClass('booking_start');
													}
													if (cnt == days - 1) {
														$("div[id='" + divid + "']").addClass('booking_end');
													}
													cnt++;
													//setting background color to div tooltip
													//Setting Tooltip on Div
													$("div[id='" + divid + "']").tooltip({

														using : function() {
															return '<div>' + this.title + '</div>';
														},
														show : {
															effect : "slideDown",
															delay : 1000
														},

														hide : {
															effect : "slideUp",
															delay : 100
														},
													});
												}// while end
											}
										}
									}
								}
							}//main for of self.reservations.length
							$(".room_booked").dblclick(function(ev){

//							console.log("room_booked::::::::::::::::::::::::::::::dblclick",ev.currentTarget.innerHTML)
							var res_info = self.get_reservation(ev.currentTarget.innerHTML);
							var view_ids=self.get_view_id();
							self.do_action({
							name: _t("Hotel Reservation"),
							res_model: 'hotel.reservation',
							views: [[view_ids, 'form']],
							res_id:res_info.id,
							view_mode:['form'],
							type: 'ir.actions.act_window',
							target: "new",

							context: {},
							});
							});//room booked dbclick end

							$(".room_booked").hover(function(ev) {
//							    console.log("room_booked::::::::::::::::::::::::::::::hover")
								var res_info = self.get_reservation(ev.currentTarget.innerHTML);
								var elements = document.getElementsByClassName("room_booked");
								for (var ele = 0; ele < elements.length; ele++) {
									if (elements[ele].innerHTML == res_info.reservation_no) {
										$("div[id='" + elements[ele].id + "']").addClass("highlight_booked");
									}
								}
								$(this).addClass("highlight_booked");
							}, function(ev) {
								var res_info = self.get_reservation(ev.currentTarget.innerHTML);
								var elements = document.getElementsByClassName("room_booked");
								for (var ele = 0; ele < elements.length; ele++) {
									if (elements[ele].innerHTML == res_info.reservation_no) {
										$("div[id='" + elements[ele].id + "']").removeClass("highlight_booked");
									}
								}
								$(this).removeClass("highlight_booked");
							});
							//end room booked hover
							var isMouseDown = false;
							$(".room_available").mousedown(function() {
								var today = new Date();
								var month='';
								var day=''

								if (today.getMonth().toString().length < 2)
								    {
                                    month = '0' + (today.getMonth()+1);
                                    }
                                else
                                    {
                                    month=(today.getMonth()+1)

                                    }


                                if (today.getDate().toString().length < 2)
                                    {
                                            day = '0' + today.getDate();
                                    }

                                else
                                    {
                                        day =today.getDate()

                                    }


                                var date = today.getFullYear()+'-'+(month)+'-'+(day);
                                var time = today.getHours() + ":" + today.getMinutes() + ":" + today.getSeconds();



								isMouseDown = true;
								var id_str = this.id.toString();
								var date1=date.toString()
								var today_date=(id_str.slice(id_str.length - 10, id_str.length)).toString()
								var selected_date = new Date(id_str.slice(id_str.length - 10, id_str.length));



								var sk=new Date().toString()

								if (date1==today_date)
								{

								$(this).removeClass("room_available");
									$(this).addClass("room_booked");
									if (self.booking_data.indexOf(this.id) < 0) {
										self.booking_data.push(this.id);
									}

								}
								else
								{

                                    if (selected_date < new Date()) {
                                        isMouseDown = false;

                                        alert('You can not book the room for this date!');
                                    } else {
                                        $(this).removeClass("room_available");
                                        $(this).addClass("room_booked");
                                        if (self.booking_data.indexOf(this.id) < 0) {
                                            self.booking_data.push(this.id);
                                        }
								}
								}
								return false;
							});
							//end room available mousedown

							$(".room_available").mouseover(function() {
								if (isMouseDown) {
									if (self.booking_data.indexOf(this.id) < 0) {
										self.booking_data.push(this.id);
									}
									$(this).removeClass("room_available");
									$(this).addClass("room_booked");
								}
							});
							//end  room_available mouseover

							//**************Book new Reservation**********************
							$(".room_available").mouseup(function() {
							    console.log("mouseup::::::::::::::::::::::::::::",self.booking_data)
								if (self.booking_data.length > 0) {
									self.booking_data.sort();
									var view_ids=self.get_view_id();
									self.do_action({
										name : _t("Hotel Reservation"),
										res_model : 'hotel.reservation',
										views : [[view_ids, 'form']],

										type : 'ir.actions.act_window',

										target : "new",
										context : {
											'booking_data' : self.booking_data,
											'shop' : parseInt($("#shops").val())
										},
										flags : {
											action_buttons : true,
										},

									});

									$("#show_dashboard").trigger('click');
								}

								self.booking_data = new Array();
								isMouseDown = false;
							});
							// end room_available mouseup

							$(document).mouseup(function() {
								isMouseDown = false;
							});
							//end doc

						}	//end reservation if

					});
					//end fetch hotel.room

					//*****************End Adding Rooms*******************************************************

				});
				//end fetch product category

			});
			//end load_data

		}, //end show dashboard

		fetch : function(model, fields, domain, ctx) {
//			return new Models(model).query(fields).filter(domain).context(ctx).all();
			var domain = domain;
			return this._rpc({
                    model: model,
                    method: 'search_read',
                    domain: domain,
                    fields: fields,
                })
		},

		get_reservation_line : function(line_id) {

//		    console.log("innnnnnnnnnnnnnnnnnnnnnnnnnnnnn1")


			for (var rline = 0; rline < this.reservation_lines.length; rline++) {
				if (this.reservation_lines[rline].id == line_id) {
					return this.reservation_lines[rline];
				}
			}

		},

		get_reservation : function(res_name) {
//		    console.log("innnnnnnnnnnnnnnnnnnnnnnnnnnnnn2")
			for (var rline = 0; rline < this.reservations.length; rline++) {
				if (this.reservations[rline].reservation_no == res_name) {
					return this.reservations[rline];
				}
			}

		},

		get_guest_info : function(guest_id) {
			var self = this;
			var guests_info = self.guest_details;
			for (var guest = 0; guest < guests_info.length; guest++) {
				if (guest_id == guests_info[guest].id) {
					return guests_info[guest];
				}
			}
		},

		get_guest_details : function(res_line) {
			var self = this;
			var id_details = reservations.id_line_ids;
			var guest_info;
			var guest_details = "<table class='tbl_guest_details'><tr><th>Guest Name</th>" + "<th>Gender</th>" + "<th>Id Card No.</th>" + "<th>Doc. Type</th>";
			for (var id = 0; id < id_details.length; id++) {
				guest_info = self.get_guest_info(id_details[id]);
				guest_details += "<tr><td>" + guest_info.partner_name + "</td>" + "<td>" + guest_info.gender + "</td>" + "<td>" + guest_info.name + "</td>" + "<td>" + guest_info.client_id[1] + "</td></tr>";
			}
			guest_details += "</table>";
			return guest_details;
		},

		//	**********************************Fetching required records from Database*******************************************

		load_data : function() {
			var self = this;
			var loaded = self.fetch('hotel.reservation.line', ['id', 'room_number', 'categ_id',  'checkin', 'checkout', 'number_of_days'], ['&', ['line_id', '!=', false], ['checkin', '<=', $("#to_date").val()]], {}).then(function(res_lines) {
				self.reservation_lines = res_lines;
				return self.fetch('hotel.reservation', ['id', 'reservation_no', 'reservation_line', 'state','id_line_ids','partner_id'], [['state', 'not in', ['cancel']]], {});
			}).then(function(reservation) {
				self.reservations = reservation;
				return self.fetch('hotel.resv.id.details', ['id', 'name', 'partner_name', 'gender', 'country_id', 'date_birth', 'client_id'], [], [], {});
			}).then(function(guest_details) {
				self.guest_details = guest_details;
				return self.fetch('hotel.housekeeping', ['id', 'current_date', 'end_date', 'room_no', 'state'], [['state', 'in', ['dirty']], ['current_date', '>=', $("#from_date").val()]], {});
			}).then(function(housekeeping_details) {
				self.housekeeping_lines = housekeeping_details;
				return self.fetch('product.product', ['id', 'product_tmpl_id'], [], [], {});
			}).then(function(productlines) {
				self.product_lines = productlines;
				return self.fetch('ir.ui.view', ['id', 'name','model','type'], [['name', '=', 'hotel.reservation.form1'],['model', '=', 'hotel.reservation'],['type','=','form']], {});
			}).then(function(views) {
				self.view_ids = views;
			});
			return loaded;
		},
		//*********************************************************************************************************************************

		get_dirty_room : function(compare_date, product_id) {
			
			for (var hline = 0; hline < this.housekeeping_lines.length; hline++) {
				if (this.housekeeping_lines[hline].room_no[0] == product_id[0]) {
					if ((this.housekeeping_lines[hline].current_date <= compare_date) && (compare_date <= this.housekeeping_lines[hline].end_date)) {
						return true;
					} else {
						return false;
					}
				}
			}
		},
		
		
		/*get_product_list : function(product_id) {
			for (var pline = 0; pline < this.product_lines.length; pline++) {
				if (this.product_lines[pline].id == product_id[0]) {
					return this.product_lines[pline].name_template;
				}
			}
		},*/
		
		get_view_id : function() {
			return this.view_ids[0].id;
			
		},
			
	});

	core.action_registry.add('room.dashboard.ui', RoomDashboardView);
	return {
		RoomDashboardView : RoomDashboardView,
	};
});
