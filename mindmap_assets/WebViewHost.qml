import QtQuick
import QtWebView

Item {
    id: root

    signal pageLoadFinished(bool successful, string errorText)
    signal javaScriptResult(int requestId, var result)

    WebView {
        id: webView
        anchors.fill: parent
        onLoadingChanged: function(loadRequest) {
            if (loadRequest.status === WebView.LoadSucceededStatus) {
                root.pageLoadFinished(true, "")
            } else if (loadRequest.status === WebView.LoadFailedStatus) {
                root.pageLoadFinished(false, loadRequest.errorString)
            }
        }
    }

    function runJavaScript(script, requestId) {
        webView.runJavaScript(script, function(result) {
            root.javaScriptResult(requestId, result)
        })
    }

    function loadHtml(html) {
        webView.loadHtml(html)
    }
}
