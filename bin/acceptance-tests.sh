#!/bin/bash
EXIT=0
BASE_URL=${1:-https://snippets.mozilla.com}
URLS=(
    "/"
    "/healthz/"
    "/readiness/"
    "/robots.txt"
    "/contribute.json"
    "/4/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/en-US/release/Windows_NT%206.1/default/default/"
    "/5/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/en-US/release/Windows_NT%206.1/default/default/"
    "/json/1/Fennec/55.0.2/20170815231002/Android_arm-eabi-gcc3/en-GB/release/Linux%2022/default/default/"
    "/feeds/snippets-enabled.ics"
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

for url in ${URLS[*]}
do
    check_http_code ${BASE_URL}${url}
done

# Check a page that throws 404. Not ideal but will surface 500s
check_http_code ${BASE_URL}/foo 404

check_zero_content_length ${BASE_URL}/4/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/xx/release/Windows_NT%206.1/default/default/
check_zero_content_length ${BASE_URL}/5/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/xx/release/Windows_NT%206.1/default/default/

exit ${EXIT}
