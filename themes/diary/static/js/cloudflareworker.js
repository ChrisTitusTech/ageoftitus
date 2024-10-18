async function handleRequest(request, env) {
  const url = new URL(request.url);
  console.log("Received request for:", url.pathname);

  if (url.pathname === '/api/check-status') {
    return await checkStatus(request, env);
  }
  
  if (url.pathname === '/api/get-last-video') {
    return await getLastVideo(request, env);
  }
  
  if (url.pathname === '/api/' || url.pathname === '/api') {
    return new Response('Welcome to the Twitch status checker API!', {
      headers: { 'Content-Type': 'text/plain' }
    });
  }
  
  return new Response(`Not Found: ${url.pathname}`, { 
    status: 404,
    headers: { 'Content-Type': 'text/plain' }
  });
}

async function checkStatus(request, env) {
  if (typeof env?.TWITCH_KV === 'undefined') {
    console.error('TWITCH_KV is not defined');
    return new Response('Configuration error: TWITCH_KV not available', { status: 500 });
  }

  try {
    let token = await env.TWITCH_KV.get('access_token')
    if (!token) {
      console.log("No existing token found, generating new one")
      token = await generateNewToken(env)
      await env.TWITCH_KV.put('access_token', token, {expirationTtl: 30 * 24 * 60 * 60}) // 30 days
    } else {
      console.log("Using existing token")
    }
    
    const status = await checkChannelStatus(token, env)
    
    return new Response(JSON.stringify(status), {
      headers: { 'Content-Type': 'application/json' }
    })
  } catch (error) {
    console.error("Error in checkStatus:", error)
    return new Response(`Error checking status: ${error.message}`, { status: 500 })
  }
}

async function generateNewToken(env) {
  const clientId = env.CLIENT_ID
  const clientSecret = env.CLIENT_SECRET
  
  console.log("Generating new token with Client ID:", clientId.substring(0, 5) + "...")

  const response = await fetch('https://id.twitch.tv/oauth2/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      grant_type: 'client_credentials',
    }),
  })

  if (!response.ok) {
    console.error("Error generating token. Status:", response.status)
    const text = await response.text()
    console.error("Response:", text)
    throw new Error(`Failed to generate token: ${response.status} ${text}`)
  }

  const data = await response.json()
  return data.access_token
}

async function checkChannelStatus(token, env) {
  const clientId = env.CLIENT_ID;
  const channelName = env.CHANNEL_NAME;

  console.log("Checking channel status for:", channelName);

  const response = await fetch(`https://api.twitch.tv/helix/streams?user_login=${channelName}`, {
    headers: {
      'Client-ID': clientId,
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    console.error("Error checking channel status. Status:", response.status);
    const text = await response.text();
    console.error("Response:", text);
    throw new Error(`Failed to check channel status: ${response.status} ${text}`);
  }

  const data = await response.json();
  return {
    isLive: data.data.length > 0,
    viewerCount: data.data.length > 0 ? data.data[0].viewer_count : 0,
    channelName: channelName,
    streamData: data.data.length > 0 ? data.data[0] : null,
  };
}

async function getLastVideo(request, env) {
  if (typeof env?.TWITCH_KV === 'undefined') {
    console.error('TWITCH_KV is not defined');
    return new Response('Configuration error: TWITCH_KV not available', { status: 500 });
  }

  const url = new URL(request.url);
  const channelName = url.searchParams.get('channel');

  if (!channelName) {
    return new Response('Channel name is required', { status: 400 });
  }

  try {
    let token = await env.TWITCH_KV.get('access_token');
    if (!token) {
      console.log("No existing token found, generating new one");
      token = await generateNewToken(env);
      await env.TWITCH_KV.put('access_token', token, {expirationTtl: 30 * 24 * 60 * 60}); // 30 days
    } else {
      console.log("Using existing token");
    }
    
    const lastVideo = await fetchLastVideo(token, env, channelName);
    
    return new Response(JSON.stringify(lastVideo), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error("Error in getLastVideo:", error);
    return new Response(`Error fetching last video: ${error.message}`, { status: 500 });
  }
}

async function fetchLastVideo(token, env, channelName) {
  const clientId = env.CLIENT_ID;

  console.log("Fetching last video for channel:", channelName);

  // First, get the user ID for the channel
  const userResponse = await fetch(`https://api.twitch.tv/helix/users?login=${channelName}`, {
    headers: {
      'Client-ID': clientId,
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!userResponse.ok) {
    console.error("Error fetching user data. Status:", userResponse.status);
    const text = await userResponse.text();
    console.error("Response:", text);
    throw new Error(`Failed to fetch user data: ${userResponse.status} ${text}`);
  }

  const userData = await userResponse.json();
  if (userData.data.length === 0) {
    throw new Error(`User not found: ${channelName}`);
  }

  const userId = userData.data[0].id;

  // Now, fetch the most recent video
  const videoResponse = await fetch(`https://api.twitch.tv/helix/videos?user_id=${userId}&type=archive&first=1`, {
    headers: {
      'Client-ID': clientId,
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!videoResponse.ok) {
    console.error("Error fetching video data. Status:", videoResponse.status);
    const text = await videoResponse.text();
    console.error("Response:", text);
    throw new Error(`Failed to fetch video data: ${videoResponse.status} ${text}`);
  }

  const videoData = await videoResponse.json();
  return videoData.data.length > 0 ? videoData.data[0] : null;
}

export default {
  async fetch(request, env, ctx) {
    try {
      return await handleRequest(request, env);
    } catch (error) {
      console.error("Error in handleRequest:", error);
      return new Response(`Server Error: ${error.message}`, { status: 500 });
    }
  }
};
