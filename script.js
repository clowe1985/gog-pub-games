document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  if (!outside || !inside || !enterBtn) {
    console.error("One of the elements is missing! Check IDs in HTML.");
    return;
  }

  enterBtn.addEventListener('click', () => {
    console.log("Enter button clicked — transitioning...");
    outside.classList.remove('active');
    setTimeout(() => {
      outside.style.display = 'none';
      inside.classList.add('active');
      // Optional: make George speak here later with TTS
      console.log("Inside pub loaded — George would roast you now");
    }, 800); // short delay for fade effect
  });

  // Telegram Mini App init (makes it feel native)
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand(); // full-screen mode
    Telegram.WebApp.MainButton.setText("Buy a Pint").show(); // example button
  }
});
