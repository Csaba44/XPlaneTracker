addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

async function handleRequest(request) {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  const url = new URL(request.url);
  const params = url.searchParams;

  const registrations = (params.get('registrations') || '').split(',').map(r => r.trim()).filter(Boolean);

  if (registrations.length === 0) {
    return jsonResponse({ error: 'No registrations provided' }, 400);
  }

  // Fetch best photo for each registration in parallel
  const results = await Promise.all(
    registrations.map(reg => fetchBestPhoto(reg))
  );

  // Build response object keyed by registration
  const output = {};
  for (let i = 0; i < registrations.length; i++) {
    output[registrations[i]] = results[i];
  }

  return jsonResponse(output);
}

async function fetchBestPhoto(registration) {
  const jetPhotosUrl = `https://www.jetphotos.com/showphotos.php?` + new URLSearchParams({
    page: '1',
    'sort-order': '0',
    'keywords-contain': '0',
    'keywords-type': 'reg',
    keywords: registration,
    aircraft: 'all',
    airline: 'all',
    'country-location': 'all',
    'photo-year': 'all',
    'photographer-group': 'all',
    category: 'all',
    genre: 'all',
    'search-type': 'Advanced',
  });

  try {
    const response = await fetch(jetPhotosUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://www.jetphotos.com/',
      }
    });

    if (!response.ok) {
      return { error: `Fetch failed: ${response.status} ${response.statusText}` };
    }

    const html = await response.text();
    const photos = await parsePhotos(html);

    if (photos.length === 0) {
      return { error: 'No photos found' };
    }

    // Pick the photo with the most likes
    const best = photos.reduce((a, b) => (parseInt(b.likes) > parseInt(a.likes) ? b : a));

    return {
      registration: best.registration,
      aircraftType: best.aircraftType,
      photographer: best.photographer,
      location: best.location,
      photoDate: best.photoDate,
      likes: best.likes,
      thumbnailUrl: best.thumbnailUrl,
      imageUrl: best.imageUrl,
      photoPageUrl: best.photoPageUrl,
    };

  } catch (error) {
    return { error: error.message };
  }
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}

// --- HTML Parsing (same HTMLRewriter logic, trimmed to needed fields) ---

function parsePhotos(html) {
  const photos = [];

  class PhotoStreamHandler {
    constructor(photosArray) {
      this.photos = photosArray;
      this.currentPhoto = null;
      this.currentStatText = '';
      this.isInsideInfoListItem = false;
      this.currentInfoListText = '';
      this.currentLinkHref = '';
      this.currentLinkText = '';
    }

    divElement(element) {
      if (element.hasAttribute('data-photo')) {
        this.currentPhoto = {
          photoId: element.getAttribute('data-photo'),
          thumbnailUrl: 'N/A',
          imageUrl: 'N/A',
          photoPageUrl: 'N/A',
          registration: 'N/A',
          aircraftType: 'N/A',
          photographer: 'N/A',
          location: 'N/A',
          photoDate: 'N/A',
          likes: '0',
        };
        element.onEndTag(() => {
          if (this.currentPhoto) {
            this.currentPhoto.aircraftType = this.currentPhoto.aircraftType.replace(/[\\/:*?"<>|]/g, '').trim() || 'Unknown';
            this.photos.push(this.currentPhoto);
            this.currentPhoto = null;
          }
        });
      }
    }

    imgElement(element) {
      if (this.currentPhoto) {
        const src = element.getAttribute('src');
        if (src) {
          this.currentPhoto.thumbnailUrl = src.startsWith('//') ? `https:${src}` : src;
          this.currentPhoto.imageUrl = this.currentPhoto.thumbnailUrl.replace('/400/', '/full/');
        }
        const altText = element.getAttribute('alt');
        if (altText) {
          const parts = altText.split('-').map(p => p.trim());
          if (parts.length >= 2) {
            this.currentPhoto.registration = parts[0];
            this.currentPhoto.aircraftType = parts[1];
          }
        }
      }
    }

    photoLinkElement(element) {
      if (this.currentPhoto) {
        const href = element.getAttribute('href');
        if (href) this.currentPhoto.photoPageUrl = `https://www.jetphotos.com${href}`;
      }
    }

    infoListItemElement(element) {
      if (!this.currentPhoto) return;
      this.isInsideInfoListItem = true;
      this.currentInfoListText = '';
      this.currentLinkHref = '';
      this.currentLinkText = '';

      element.onEndTag(() => {
        if (!this.currentPhoto) return;
        this.isInsideInfoListItem = false;

        const fullText = this.currentInfoListText.trim();
        let valueToUse = this.currentLinkText ? this.currentLinkText.trim() : fullText;

        if (!this.currentLinkText) {
          if (fullText.includes('Reg:')) valueToUse = fullText.replace('Reg:', '').trim().split(' ')[0];
          else if (fullText.includes('Aircraft:')) valueToUse = fullText.replace('Aircraft:', '').trim();
          else if (fullText.includes('Location:')) valueToUse = fullText.replace('Location:', '').trim();
          else if (fullText.includes('Photo date:')) valueToUse = fullText.replace('Photo date:', '').trim();
          else if (fullText.includes('By:') || fullText.includes('Photographer:'))
            valueToUse = fullText.replace('By:', '').replace('Photographer:', '').trim();
        }

        if (fullText.includes('Reg:')) this.currentPhoto.registration = valueToUse;
        else if (fullText.includes('Aircraft:')) this.currentPhoto.aircraftType = valueToUse;
        else if (fullText.includes('Location:')) this.currentPhoto.location = valueToUse;
        else if (fullText.includes('Photo date:')) this.currentPhoto.photoDate = valueToUse;
        else if (fullText.includes('By:') || fullText.includes('Photographer:'))
          this.currentPhoto.photographer = valueToUse;
      });
    }

    infoListTextAccumulator(textChunk) {
      if (this.isInsideInfoListItem) this.currentInfoListText += textChunk.text;
    }

    linkInInfoTextElement(element) {
      if (this.currentPhoto && this.isInsideInfoListItem) {
        this.currentLinkHref = element.getAttribute('href');
        this.currentLinkText = '';
      }
    }

    linkTextInInfoTextAccumulator(textChunk) {
      if (this.currentPhoto && this.isInsideInfoListItem && this.currentLinkHref)
        this.currentLinkText += textChunk.text;
    }

    statElement(element) {
      if (this.currentPhoto) {
        this.currentStatText = '';
        element.onEndTag(() => {
          const text = this.currentStatText;
          const valueMatch = text.match(/\d+/);
          const value = valueMatch ? valueMatch[0] : '0';
          if (text.includes('Likes:')) this.currentPhoto.likes = value;
        });
      }
    }

    statTextAccumulator(textChunk) {
      if (this.currentPhoto) this.currentStatText += textChunk.text;
    }
  }

  const handler = new PhotoStreamHandler(photos);

  return new HTMLRewriter()
    .on('div[data-photo]', { element: handler.divElement.bind(handler) })
    .on('img.result__photo', { element: handler.imgElement.bind(handler) })
    .on('a.result__photoLink', { element: handler.photoLinkElement.bind(handler) })
    .on('.result__infoListText', {
      element: handler.infoListItemElement.bind(handler),
      text: handler.infoListTextAccumulator.bind(handler)
    })
    .on('.result__infoListText a', {
      element: handler.linkInInfoTextElement.bind(handler),
      text: handler.linkTextInInfoTextAccumulator.bind(handler)
    })
    .on('.result__stat', {
      element: handler.statElement.bind(handler),
      text: handler.statTextAccumulator.bind(handler)
    })
    .transform(new Response(html))
    .text()
    .then(() => photos);
}