document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Make sure pub starts visible
  outside.classList.add('active');
  inside.classList.remove('active');
  inside.style.opacity = '0';

  // Enter button — straight to inside pub, no wallet nonsense
  enterBtn.addEventListener('click', () => {
    outside.style.opacity = '0';
    setTimeout(() => {
      outside.style.display = 'none';
      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 1200);
  });

  // Telegram init (keep it)
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // Game switching
  function showGame(gameId) {
    const pub = document.getElementById('view-inside');
    pub.classList.remove('active');
    pub.style.opacity = '0';

    const gameScreen = document.getElementById('game-' + gameId);
    setTimeout(() => {
      pub.style.display = 'none';
      gameScreen.style.display = 'block';
      gameScreen.classList.add('visible');

      if (gameId === 'football') {
        loadFootballCard();  // this loads the teams
      }
    }, 1000);
  }

  function backToPub() {
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
    }, 1000);
  }

  // Football Card teams & grid loader
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
      console.error("No #football-grid div found!");
      return;
    }
    grid.innerHTML = '';
    footballTeams.forEach((team, index) => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `
        <div>${team}</div>
        <div class="username">[Pick Me]</div>
      `;
      slot.onclick = () => pickTeam(index, team, slot);
      grid.appendChild(slot);
    });
    console.log("Football grid loaded with 32 teams");
  }

  function pickTeam(index, team, slot) {
    if (!confirm(`Claim ${team} for $1?`)) return;
    const username = Telegram.WebApp.initDataUnsafe.user?.username || "You";
    slot.querySelector('.username').textContent = `@${username}`;
    slot.classList.add('claimed');
    slot.onclick = null;
    console.log(`Claimed ${team} by @${username}`);
  }

  window.showGame = showGame;
  window.backToPub = backToPub;
});
