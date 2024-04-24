document.getElementById('searchForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const query = document.getElementById('queryInput').value;
    fetch(`/search?query=${encodeURIComponent(query)}`, {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        const results = document.getElementById('results');
        results.innerHTML = '';  // Clear previous results
        if (data.length === 0) {
            results.innerHTML = '<p><i class="fas fa-info-circle"></i> لا توجد نتائج.</p>';
        } else {
            data.forEach(item => {
                const div = document.createElement('div');
                const title = document.createElement('h3');
                title.textContent = item.title;
                const videoDetails = extractVideoIDAndStartTime(item.link);
                const videoFrame = document.createElement('iframe');
                videoFrame.setAttribute('src', `https://www.youtube.com/embed/${videoDetails.id}?start=${videoDetails.startTime}`);
                videoFrame.setAttribute('allowfullscreen', true);
                
                div.appendChild(title);
                div.appendChild(videoFrame);
                results.appendChild(div);
            });
        }
        // Move the search bar to the center
        const searchContainer = document.querySelector('.search-container');
        searchContainer.classList.add('results-shown');
    })
    .catch(error => {
        console.error('Error:', error);
        const results = document.getElementById('results');
        results.innerHTML = '<p><i class="fas fa-exclamation-triangle"></i> حدث خطأ أثناء جلب النتائج.</p>';
    });
});

function extractVideoIDAndStartTime(url) {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    const match = url.match(regExp);
    const videoID = (match && match[2].length == 11) ? match[2] : null;
    const startTimeParam = url.split('&t=')[1];
    const startTime = startTimeParam ? parseInt(startTimeParam, 10) : 0;
    return { id: videoID, startTime: startTime };
}
