document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  enterBtn.addEventListener('click', () => {
    outside.classList.remove('active');
    inside.classList.add('active');
  });

  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }
});

function showGame(gameId) {
  const pub = document.getElementById('view-inside');
  const gameScreen = document.getElementById('game-' + gameId);

  pub.classList.remove('active');

  document.querySelectorAll('.game-screen').forEach(screen => {
    screen.classList.remove('visible');
  });

  gameScreen.classList.add('visible');
}

function backToPub() {
  document.querySelectorAll('.game-screen').forEach(screen => {
    screen.classList.remove('visible');
  });

  const pub = document.getElementById('view-inside');
  pub.classList.add('active');
}
