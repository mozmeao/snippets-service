#!/bin/bash
EXIT=0
BASE_URL=${1:-https://snippets.mozilla.com}
URLS=(
    "/"
    "/healthz/"
    "/readiness/"
    "/robots.txt"
    "/contribute.json"
    "/5/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/en-US-test/release/Windows_NT%206.1/default/default/"
    "/6/Firefox/62.0.1/20160922113459/WINNT_x86-msvc/en-US-test/release/Windows_NT%206.1/default/default/"
    "/feeds/snippets.ics"
)

function check_http_code {
    echo -n "Checking URL ${1} "
    curl -k -L -s -o /dev/null -I -w "%{http_code}" $1 | grep ${2:-200} > /dev/null
    if [ $? -eq 0 ];
    then
        echo "OK"
    else
        echo "Failed"
        EXIT=1
    fi
}

function check_zero_content_length {
    echo -n "Checking zero content length of URL ${1} "
    test=$(curl -L -s ${1} | wc -c);
    if [[ $test -eq 0 ]];
    then
        echo "OK"
    else
        echo "Failed"
        EXIT=1
    fi
}

function check_empty_json {
    echo -n "Checking empty json for URL ${1} "
    test=$(curl -L -s ${1});
    if [ $test = '{}' ];
    then
        echo "OK"
    else
        echo "Failed"
        EXIT=1
    fi
}

for url in ${URLS[*]}
do
    check_http_code ${BASE_URL}${url}
done

# Check a page that throws 404. Not ideal but will surface 500s
check_http_code ${BASE_URL}/foo 404

check_zero_content_length ${BASE_URL}/4/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/xx/release/Windows_NT%206.1/default/default/
check_zero_content_length ${BASE_URL}/5/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/xx/release/Windows_NT%206.1/default/default/
check_empty_json ${BASE_URL}/6/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/xx/release/Windows_NT%206.1/default/default/

exit ${EXIT}
