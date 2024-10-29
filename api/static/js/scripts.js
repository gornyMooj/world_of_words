$("form[name=login_form]").submit(function(e) {
  var $form = $(this);
  var $error = $form.find(".error");
  var data = $form.serialize();

  $.ajax({
    url: "/user/login",
    type: "POST",
    data: data,
    dataType: "json",
    success: function(resp) {
      // On success, redirect to the home page
      window.location.href = "/home";
    },
    error: function(resp) {
      // Log the full error response to the console for debugging
      console.error("Error response:", resp);
      console.error("window.location.href:", window.location.href);

      // Check if responseJSON exists and has an error property
      var errorMessage = resp.responseJSON && resp.responseJSON.error ? 
                         resp.responseJSON.error : 
                         "An unexpected error occurred.";
      $error.text(errorMessage).removeClass("error--hidden");
    }
  });

  e.preventDefault();
});

$("form[name=signup_form]").submit(function(e) {
  var $form = $(this);
  var $error = $form.find(".error");
  var data = $form.serialize();

  $.ajax({
    url: "/user/signup",
    type: "POST",
    data: data,
    dataType: "json",
    success: function(resp) {
      // On success, redirect to the home page
      window.location.href = "/home";
    },
    error: function(resp) {
      // Log the full error response to the console for debugging
      console.error("Error response:", resp);

      // Check if responseJSON exists and has an error property
      var errorMessage = resp.responseJSON && resp.responseJSON.error ? 
                         resp.responseJSON.error : 
                         "An unexpected error occurred.";
      $error.text(errorMessage).removeClass("error--hidden");
    }
  });

  e.preventDefault();
});
