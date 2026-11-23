function handler(event) {
    var response = event.response;
    var headers = response.headers;

    headers['content-security-policy'] = {
        value: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'; upgrade-insecure-requests"
    };
    headers['permissions-policy'] = {
        value: 'geolocation=(), camera=(), microphone=(), payment=(), usb=()'
    };
    headers['strict-transport-security'] = {
        value: 'max-age=31536000; includeSubDomains'
    };
    headers['x-frame-options'] = {
        value: 'SAMEORIGIN'
    };
    headers['x-content-type-options'] = {
        value: 'nosniff'
    };
    headers['referrer-policy'] = {
        value: 'strict-origin-when-cross-origin'
    };

    return response;
}
