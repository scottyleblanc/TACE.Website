function handler(event) {
    var request = event.request;
    var uri = request.uri;

    if (uri.slice(-1) === '/') {
        request.uri += 'index.html';
    } else if (uri.lastIndexOf('.') === -1) {
        request.uri += '/index.html';
    }

    return request;
}
