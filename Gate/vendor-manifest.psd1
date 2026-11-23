@{
    # Third-party files vendored under hugo/static, checked by Gate/Invoke-UnitTest.ps1
    # (step 4): every file under VendorRoots must be listed here, and its SHA-256 must
    # match. Update an entry only after replacing the file from the stated source
    # package (npm pack <package>@<version>) and reviewing the change.
    #
    # [SEC] The site loads no script, style or font from a third-party host; these
    # pinned copies are the only third-party code it serves. .gitattributes marks the
    # roots -text so line endings, and therefore hashes, are the same on every platform.

    SchemaVersion = 1

    VendorRoots = @(
        'hugo/static/js/vendor'
        'hugo/static/fonts'
    )

    Files = @(
        @{ Path = 'hugo/static/fonts/dm-mono/5.3.0/dm-mono-latin-400-normal.woff2'; Source = 'npm @fontsource/dm-mono@5.3.0'; Sha256 = 'e1896b13b2b1bb112fac2f9571bd6c40e118746e77a4511edbf43fbb41bf3e1e' }
        @{ Path = 'hugo/static/fonts/dm-mono/5.3.0/dm-mono-latin-500-normal.woff2'; Source = 'npm @fontsource/dm-mono@5.3.0'; Sha256 = '9964608a849396bd00c4bfd7034afe03486469dcf20b4f6b8cbdfdd310369951' }
        @{ Path = 'hugo/static/fonts/dm-mono/5.3.0/LICENSE'; Source = 'npm @fontsource/dm-mono@5.3.0'; Sha256 = 'd2766c396a8534cba53340f8af2037749b6a0a1dd3587348c917a70e779d2e32' }
        @{ Path = 'hugo/static/fonts/fraunces/5.3.0/fraunces-latin-opsz-italic.woff2'; Source = 'npm @fontsource-variable/fraunces@5.3.0'; Sha256 = '066710ce7ed235a339d3d6cdcc8b55c0bea5632232662d83aacea25852108271' }
        @{ Path = 'hugo/static/fonts/fraunces/5.3.0/fraunces-latin-opsz-normal.woff2'; Source = 'npm @fontsource-variable/fraunces@5.3.0'; Sha256 = '7234ed860a9cc83045413c4faee63c960a8f2d1917adcf728119307d56e0d783' }
        @{ Path = 'hugo/static/fonts/fraunces/5.3.0/LICENSE'; Source = 'npm @fontsource-variable/fraunces@5.3.0'; Sha256 = 'cd3384cafac6f2bddc3955273958a2e029f97027c8037ac539ef5744a77b579e' }
        @{ Path = 'hugo/static/fonts/ibm-plex-mono/5.3.0/ibm-plex-mono-latin-400-normal.woff2'; Source = 'npm @fontsource/ibm-plex-mono@5.3.0'; Sha256 = '08949f728dc52d528e69b1667d15c89a5686a4ee9a296ff90983985f99c380f7' }
        @{ Path = 'hugo/static/fonts/ibm-plex-mono/5.3.0/ibm-plex-mono-latin-500-normal.woff2'; Source = 'npm @fontsource/ibm-plex-mono@5.3.0'; Sha256 = '01d285447409c8a588692162439a038b8cbd7871309ee20267b0d2d91c6e8e22' }
        @{ Path = 'hugo/static/fonts/ibm-plex-mono/5.3.0/ibm-plex-mono-latin-600-normal.woff2'; Source = 'npm @fontsource/ibm-plex-mono@5.3.0'; Sha256 = '0d1f0b8d0722224e32e9f28261bdc86c79115be73444ae5eceb73976a1bcdf83' }
        @{ Path = 'hugo/static/fonts/ibm-plex-mono/5.3.0/LICENSE'; Source = 'npm @fontsource/ibm-plex-mono@5.3.0'; Sha256 = '23b0a9d0c6d3f140a0b77e483c5cfa6bba574325ef5cb189ed9f2fec4884533f' }
        @{ Path = 'hugo/static/fonts/newsreader/5.3.0/LICENSE'; Source = 'npm @fontsource-variable/newsreader@5.3.0'; Sha256 = '26028ec4e13b650065fa525a09532176f8a668b76ff849ea01c564a7480f91e7' }
        @{ Path = 'hugo/static/fonts/newsreader/5.3.0/newsreader-latin-opsz-italic.woff2'; Source = 'npm @fontsource-variable/newsreader@5.3.0'; Sha256 = '5dfcd10d24af8c82927ba57f7983dd997f7b200594c09c35a1b1ed9fc4597506' }
        @{ Path = 'hugo/static/fonts/newsreader/5.3.0/newsreader-latin-opsz-normal.woff2'; Source = 'npm @fontsource-variable/newsreader@5.3.0'; Sha256 = '6e4f2958c3a7c4a80acde4e5a679abe7e01bc1e30b92be3c7a8b696ef401d101' }
        @{ Path = 'hugo/static/js/vendor/mermaid/12.3.0/LICENSE'; Source = 'npm mermaid@12.3.0'; Sha256 = 'ec9fb67dcb25eccc416ed56e1aab819222c805a2a4bfe4cb19e7556bf2ffde80' }
        @{ Path = 'hugo/static/js/vendor/mermaid/12.3.0/mermaid.min.js'; Source = 'npm mermaid@12.3.0 (dist/mermaid.min.js)'; Sha256 = '336df803d87a38b70a01e736e666c8f7601d2ce42f5e47c8fafe5d721074b9a3' }
    )
}
