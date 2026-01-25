document.addEventListener('DOMContentLoaded', () => {

  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');
  const gameScreens = document.querySelectorAll('.game-screen');

  // ---------- HARD RESET STATE ----------
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';

  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  gameScreens.forEach(screen => {
    screen.style.display = 'none';
    screen.classList.remove('visible');
  });

  // ---------- ENTER PUB ----------
  enterBtn.addEventListener('click', () => {
    outside.style.opacity = '0';

    setTimeout(() => {
      outside.style.display = 'none';
      outside.classList.remove('active');

      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 1000);
  });

  // ---------- SHOW GAME ----------
  window.showGame = function (gameId) {
    inside.style.opacity = '0';

    setTimeout(() => {
      inside.style.display = 'none';
      inside.classList.remove('active');

      gameScreens.forEach(screen => {
        screen.style.display = 'none';
        screen.classList.remove('visible');
      });

      const game = document.getElementById('game-' + gameId);
      if (!game) return;

      game.style.display = 'block';
      game.classList.add('visible');
      game.style.opacity = '1';

      if (gameId === 'football') {
        loadFootballCard();
      }
    }, 600);
  };

  // ---------- BACK TO PUB ----------
  window.backToPub = function () {
    gameScreens.forEach(screen => {
      screen.style.opacity = '0';
    });

    setTimeout(() => {
      gameScreens.forEach(screen => {
        screen.style.display = 'none';
        screen.classList.remove('visible');
      });

      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 600);
  };

  // ---------- FOOTBALL CARD ----------
  const footballTeams = [
    "Arsenal","Ajax","Bournemouth","Brentford","Brighton","Burnley",
    "Chelsea","Crystal Palace","Everton","Fulham","Liverpool","Luton",
    "Man City","Man United","Newcastle","Nottingham Forest","Sheffield Utd",
    "Tottenham","West Ham","Wolves","Leicester","Leeds","Southampton",
    "Blackburn","Birmingham","Coventry","Ipswich","Middlesbrough","Norwich",
    "Preston","QPR","Sheffield Wed"
  ];

  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid || grid.children.length) return;

    footballTeams.forEach(team => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `
        <div>${team}</div>
        <div class="username">[Pick Me]</div>
      `;
      grid.appendChild(slot);
    });
  }

});
