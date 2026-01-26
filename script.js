document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Force start on outside view
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';
  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  // Hide all games at start
  document.querySelectorAll('.game-screen').forEach(screen => {
    screen.style.display = 'none';
    screen.classList.remove('visible');
  });

  // Enter pub
  enterBtn.addEventListener('click', () => {
    outside.style.opacity = '0';
    setTimeout(() => {
      outside.style.display = 'none';
      outside.classList.remove('active');
      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 1200);
  });

  // Telegram init
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // Show game
  window.showGame = function(gameId) {
    const pub = document.getElementById('view-inside');
    pub.style.opacity = '0';
    setTimeout(() => {
      pub.style.display = 'none';
      pub.classList.remove('active');
      const game = document.getElementById('game-' + gameId);
      game.style.display = 'block';
      game.classList.add('visible');
      game.style.opacity = '1';
      if (gameId === 'football') {
        loadFootballCard();
      }
    }, 1000);
  };

  // Back to pub
  window.backToPub = function() {
    document.querySelectorAll('.game-screen').forEach(screen => {
      screen.style.opacity = '0';
    });
    setTimeout(() => {
      document.querySelectorAll('.game-screen').forEach(screen => {
        screen.style.display = 'none';
        screen.classList.remove('visible');
      });
      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 1000);
  };

  // Football teams
  const footballTeams = [
    "Arsenal", "Ajax", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
    "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
    "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
    "Preston", "QPR", "Sheffield Wed"
  ];

  // Load football grid
  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) {
      console.error("Football grid div missing, you idiot.");
      return;
    }
    grid.innerHTML = '';
    footballTeams.forEach(team => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `
        <div>${team}</div>
        <div class="username">[Pick Me]</div>
      `;
      slot.onclick = () => pickTeam(team, slot);
      grid.appendChild(slot);
    });
  }

  function pickTeam(team, slot) {
    if (!confirm(`Claim ${team} for $1?`)) return;
    const username = Telegram.WebApp.initDataUnsafe.user?.username || "You";
    slot.querySelector('.username').textContent = `@${username}`;
    slot.classList.add('claimed');
    slot.onclick = null;
  }
});
