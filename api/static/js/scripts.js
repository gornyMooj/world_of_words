$("form[name=login_form").submit(function(e) {

    var $form = $(this);
    var $error = $form.find(".error");
    var data = $form.serialize();

    $.ajax({
      url: "/user/login",
      type: "POST",
      data: data,
      dataType: "json",
      success: function(resp) {
        // on sucess redirects to the page
        window.location.href = "/home";
      },
      error: function(resp) {
        $error.text(resp.responseJSON.error).removeClass("error--hidden");
      }
    });
  
    e.preventDefault();
  });
  $("form[name=signup_form").submit(function(e) {

    var $form = $(this);
    var $error = $form.find(".error");
    var data = $form.serialize();

    $.ajax({
      url: "/user/signup",
      type: "POST",
      data: data,
      dataType: "json",
      success: function(resp) {
        // on sucess redirects to the page
        window.location.href = "/home";
      },
      error: function(resp) {
        $error.text(resp.responseJSON.error).removeClass("error--hidden");
      }
    });
  
    e.preventDefault();
  });
