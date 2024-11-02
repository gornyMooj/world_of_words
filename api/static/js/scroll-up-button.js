let mybutton = document.getElementById("scroll-upp-button");

window.onscroll = function() {scrollFunction()};

function scrollFunction() {
  if (document.body.scrollTop > 100 || document.documentElement.scrollTop > 100) {
    mybutton.style.display = "block";
  } else {
    mybutton.style.display = "none";
  }
}

// When the user clicks on the button, scroll to the top of the document
function flyUp() {
  document.body.scrollTop = 0;
  document.documentElement.scrollTop = 0;
}