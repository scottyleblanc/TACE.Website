const synthetics = require('Synthetics');
const log = require('SyntheticsLogger');

const checkSite = async function () {
    const validateResponse = async function (res) {
        return new Promise((resolve, reject) => {
            if (res.statusCode < 200 || res.statusCode > 299) {
                reject(new Error('Expected HTTP 2xx, got ' + res.statusCode));
            }
            res.on('data', () => {});
            res.on('end', () => {
                log.info('Status code: ' + res.statusCode);
                resolve();
            });
        });
    };

    const requestOptions = {
        hostname: 'tacedata.ca',
        method: 'GET',
        path: '/',
        port: 443,
        protocol: 'https:',
        headers: {
            'User-Agent': 'Mozilla/5.0 (compatible; CloudWatchSynthetics/1.0)'
        }
    };

    const stepConfig = {
        includeRequestHeaders: false,
        includeResponseHeaders: false,
        includeRequestBody: false,
        includeResponseBody: false,
        restrictedHeaders: [],
        restrictedUrlParameters: []
    };

    await synthetics.executeHttpStep('Check tacedata.ca', requestOptions, validateResponse, stepConfig);
};

exports.handler = async () => {
    return await checkSite();
};
