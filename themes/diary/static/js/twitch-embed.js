const channelName = 'TitusTechGaming';
const clientId = 'au9081y3ft41wtb1p4im5502qy5emu';

async function checkLiveStatus() {
  const twitchEmbedElement = document.getElementById('twitch-embed');
  
  if (!twitchEmbedElement) {
    console.error('Twitch embed element not found');
    return;
  }

  console.log('Checking live status...');
  try {
    console.log('Fetching from worker...');
    const response = await fetch('https://twitch-token-renewer.dfm-titus.workers.dev', {
      headers: {
        'Client-ID': clientId
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Response from worker:', data);

    if (data.isLive) {
      console.log('Channel is live, updating embed');
      // Channel is live
      twitchEmbedElement.innerHTML = `
        <iframe
          src="https://player.twitch.tv/?channel=${channelName}&parent=${window.location.hostname}"
          height="480"
          width="100%"
          allowfullscreen>
        </iframe>
      `;
    } else {
      console.log('Channel is offline, clearing embed');
      // Channel is offline
      twitchEmbedElement.innerHTML = '';
    }
  } catch (error) {
    console.error('Error checking Twitch live status:', error);
  }
}

// Check live status when the page loads
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM loaded, checking live status');
  checkLiveStatus();
});

// Check live status every 5 minutes
setInterval(() => {
  console.log('Interval triggered, checking live status');
  checkLiveStatus();
}, 5 * 60 * 1000);
