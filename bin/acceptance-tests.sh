#!/bin/bash
EXIT=0
BASE_URL=${1:-https://snippets.mozilla.com}
URLS=(
    "/"
    "/healthz/"
    "/robots.txt"
    "/contribute.json"
    "/4/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/en-US/release/Windows_NT%206.1/default/default/"
    "/5/Firefox/56.0.1/20160922113459/WINNT_x86-msvc/en-US/release/Windows_NT%206.1/default/default/"
    "/json/1/Fennec/55.0.2/20170815231002/Android_arm-eabi-gcc3/en-GB/release/Linux%2022/default/default/"
)

function check_http_code {
    echo -n "Checking URL ${1} "
    curl -L -s -o /dev/null -I -w "%{http_code}" $1 | grep ${2:-200} > /dev/null
    if [ $? -eq 0 ];
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

exit ${EXIT}
