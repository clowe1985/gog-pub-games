document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Force correct initial state
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';
  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  // Hide all game screens at start
  document.querySelectorAll('.game-screen').forEach(screen => {
    screen.style.display = 'none';
    screen.classList.remove('visible');
  });

  // Enter pub button
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

  // Show game screen
  window.showGame = function(gameId) {
    const pub = document.getElementById('view-inside');
    pub.classList.remove('active');
    pub.style.opacity = '0';

    const gameScreen = document.getElementById('game-' + gameId);
    if (!gameScreen) return;

    setTimeout(() => {
      pub.style.display = 'none';
      gameScreen.style.display = 'block';
      gameScreen.classList.add('visible');
      gameScreen.style.opacity = '1';

      // Load interactive content only when tab opens
      if (gameId === 'football') {
        loadFootballCard();
      }
    }, 600);
  };

  // Back to pub
  window.backToPub = function() {
    document.querySelectorAll('.game-screen').forEach(screen => {
      screen.classList.remove('visible');
      screen.style.opacity = '0';
    });

    setTimeout(() => {
      document.querySelectorAll('.game-screen').forEach(screen => {
        screen.style.display = 'none';
      });
      const pub = document.getElementById('view-inside');
      pub.style.display = 'flex';
      pub.classList.add('active');
      pub.style.opacity = '1';
    }, 600);
  };

  // Football card loader
  const footballTeams = [
    "Arsenal", "Ajax", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
    "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
    "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
    "Preston", "QPR", "Sheffield Wed"
  ];

  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) {
      console.error("football-grid not found!");
      return;
    }
    grid.innerHTML = ''; // clear old content
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
    console.log("Football grid loaded - 32 teams ready");
  }

  function pickTeam(team, slot) {
    if (!confirm(`Claim ${team} for $1?`)) return;
    const username = Telegram.WebApp.initDataUnsafe.user?.username || "You";
    slot.querySelector('.username').textContent = `@${username}`;
    slot.classList.add('claimed');
    slot.onclick = null;
    console.log(`Claimed ${team} by @${username}`);
  }
});
