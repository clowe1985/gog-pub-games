document.addEventListener('DOMContentLoaded', () => {
  // Debug logging
  console.log(">>> SCRIPT LOADED");
  console.log(">>> Telegram WebApp available:", typeof Telegram !== 'undefined');
  if (typeof Telegram !== 'undefined') {
      console.log(">>> WebApp version:", Telegram.WebApp.version);
      console.log(">>> Init Data:", Telegram.WebApp.initData);
      console.log(">>> User:", Telegram.WebApp.initDataUnsafe.user);
  }

  // View elements
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Set initial view states
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';
  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  // Hide all game screens
  document.querySelectorAll('.game-screen').forEach(s => {
    s.style.display = 'none';
    s.classList.remove('visible');
  });

  // Enter pub button handler
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

  // Initialize Telegram WebApp
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // Show game screen function
  window.showGame = function(gameId) {
    inside.style.opacity = '0';
    setTimeout(() => {
      inside.style.display = 'none';
      inside.classList.remove('active');
      const screen = document.getElementById('game-' + gameId);
      if (!screen) return console.error("Missing screen:", gameId);
      screen.style.display = 'block';
      screen.classList.add('visible');
      screen.style.opacity = '1';
      if (gameId === 'football') loadFootballCard();
    }, 800);
  };

  // Back to pub function
  window.backToPub = function() {
    document.querySelectorAll('.game-screen').forEach(s => s.style.opacity = '0');
    setTimeout(() => {
      document.querySelectorAll('.game-screen').forEach(s => {
        s.style.display = 'none';
        s.classList.remove('visible');
      });
      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 800);
  };

  // ========== FOOTBALL CARD LOGIC ==========

  // FOOTBALL TEAMS - MUST MATCH PYTHON BOT EXACTLY (32 teams)
  const footballTeams = [
    "Arsenal", "Ajax", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
    "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
    "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
    "Preston", "QPR", "Sheffield Wed"
  ];

  // Load football card grid
  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) return console.error("Grid missing");

    grid.innerHTML = '';

    footballTeams.forEach(team => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `
        <div class="team-name">${team}</div>
        <div class="username">[Pick Me]</div>
      `;
      slot.onclick = () => pickTeam(team, slot);
      grid.appendChild(slot);
    });

    console.log(">>> Football grid loaded with", footballTeams.length, "teams");
    loadSavedClaims();
  }

  // Pick a team
  function pickTeam(team, slot) {
    const user = Telegram.WebApp.initDataUnsafe.user;

    // Check if user has Telegram username
    if (!user || !user.username) {
      alert("❌ No Telegram username found!\n\nPlease set a username in your Telegram settings:\n1. Open Telegram\n2. Go to Settings\n3. Set a Username\n4. Try again");
      return;
    }

    const username = '@' + user.username;

    // Confirm claim
    if (!confirm(`Claim ${team} for $1 USDC as ${username}?`)) {
      return;
    }

    // Visual feedback - show processing
    slot.style.opacity = '0.7';
    slot.querySelector('.username').textContent = 'Processing...';
    slot.style.pointerEvents = 'none';

    // Send claim to bot
    const claimData = {
      action: "claim_team",
      team: team,
      username: username
    };

    console.log(">>> Sending claim to bot:", claimData);

    try {
      Telegram.WebApp.sendData(JSON.stringify(claimData));
      console.log(">>> Claim sent successfully");

      // Request updated state after delay
      setTimeout(() => {
        console.log(">>> Requesting updated card state...");
        Telegram.WebApp.sendData(JSON.stringify({
          action: "get_card_state"
        }));
      }, 1500);

    } catch (error) {
      console.error(">>> Error sending data:", error);
      alert("❌ Error sending claim. Please try again.");

      // Reset slot on error
      slot.style.opacity = '1';
      slot.querySelector('.username').textContent = '[Pick Me]';
      slot.style.pointerEvents = 'auto';
    }
  }

  // Load saved claims from bot
  async function loadSavedClaims() {
    console.log(">>> Loading saved claims from bot...");
    Telegram.WebApp.sendData(JSON.stringify({
      action: "get_card_state"
    }));
  }

  // Update grid with claims
  function updateGrid(claims) {
    console.log(">>> Updating grid with claims:", claims);

    const slots = document.querySelectorAll('.team-slot');
    let updatedCount = 0;

    slots.forEach(slot => {
      const team = slot.querySelector('.team-name').textContent.trim();
      const claimed = claims[team];

      if (claimed) {
        // Add @ symbol if not already present
        const displayName = claimed.startsWith('@') ? claimed : '@' + claimed;
        slot.querySelector('.username').textContent = displayName;
        slot.classList.add('claimed');
        slot.onclick = null;
        slot.style.opacity = '1';
        slot.style.pointerEvents = 'none';
        updatedCount++;
      } else {
        // Reset any processing slots that weren't claimed
        if (slot.style.opacity === '0.7') {
          slot.style.opacity = '1';
          slot.querySelector('.username').textContent = '[Pick Me]';
          slot.style.pointerEvents = 'auto';
        }
      }
    });

    console.log(`>>> Updated ${updatedCount} claimed teams`);
  }

  // Handle data received from bot
  Telegram.WebApp.onEvent('web_app_data', (event) => {
    const data = event.data;
    if (typeof data !== 'string') return;

    console.log(">>> Received from bot:", data.substring(0, 200) + (data.length > 200 ? '...' : ''));

    // Handle claim denied
    if (data.startsWith("CLAIM_DENIED:")) {
      const errorMsg = data.replace('CLAIM_DENIED:', '').trim();
      console.error(">>> Claim denied:", errorMsg);
      alert("❌ Claim failed:\n" + errorMsg);

      // Reset all processing slots
      const slots = document.querySelectorAll('.team-slot');
      slots.forEach(slot => {
        if (slot.style.opacity === '0.7') {
          slot.style.opacity = '1';
          slot.querySelector('.username').textContent = '[Pick Me]';
          slot.style.pointerEvents = 'auto';
        }
      });
    }
    // Handle claim success
    else if (data.includes("CLAIM_SUCCESS")) {
      console.log(">>> Claim successful!");
      // Bot will send CARD_STATE next
    }
    // Handle card state
    else if (data.startsWith("CARD_STATE:")) {
      try {
        const json = data.replace('CARD_STATE:', '');
        const state = JSON.parse(json);
        updateGrid(state.teams || state);
      } catch (e) {
        console.error(">>> Error parsing card state:", e);
      }
    }
    // Handle other bot responses
    else if (data.includes("✅ Bot received test") || data.includes("✅ CLAIM_SUCCESS")) {
      console.log(">>> Bot action successful:", data.substring(0, 100));
    }
  });

  // Debug check after load
  setTimeout(() => {
    console.log("=== TELEGRAM WEBAPP STATUS ===");
    console.log("Available:", typeof Telegram !== 'undefined');
    console.log("Version:", Telegram?.WebApp?.version || 'N/A');
    console.log("User:", Telegram?.WebApp?.initDataUnsafe?.user || 'No user data');
    console.log("Username:", Telegram?.WebApp?.initDataUnsafe?.user?.username || 'No username');
    console.log("InitData present:", Telegram?.WebApp?.initData ? 'Yes (' + Telegram.WebApp.initData.length + ' chars)' : 'No');
    console.log("==============================");
  }, 2000);
});
