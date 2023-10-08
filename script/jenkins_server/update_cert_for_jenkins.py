#!/usr/local/bin/python3
#

""" Script check SSL cert renewal status daily and update it into Jenkins server if needed.

If failed to be triggered in cron, manually do the update as follows:
1. Check whether the certs files are renewed successfully under
   `/Users/me/.acme.sh/my.domain.net`
2. % acme.sh --toPkcs -d my.domain.net 
3. % keytool -importkeystore -srckeystore /Users/me/.acme.sh/my.domain.net/my.domain.net.pfx -srcstoretype pkcs12 -destkeystore ~/.jenkins/jenkins.jks -srcstorepass 'MyPkcsPwd' -deststorepass 'MyPkcsPwd' -noprompt
4. % brew services restart jenkins

"""
import datetime
import os
import subprocess

from .config import *


def log(content, stdout_fw):
    stdout_fw.write(f"{datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')} - {content}\n")
    print(content)


def import_jks_and_restart_jenkins(stdout_fw):
    p = subprocess.Popen(f"{ACME_SH_DIR}/acme.sh --toPkcs -d {DOMAIN} --password '{PKCS_PWD}'",
                         shell=True, stdout=stdout_fw)
    r = p.wait()
    if r != 0:
        log(f'!!!Export to Pkcs failed.', stdout_fw)
        raise RuntimeError
    log(f'Export to Pkcs result={p.returncode}', stdout_fw)

    p = subprocess.Popen(
        "/usr/bin/keytool -importkeystore -srckeystore "
        f"{ACME_SH_DIR}/{DOMAIN}/{DOMAIN}.pfx "
        "-srcstoretype pkcs12 -destkeystore {JENKINS_JKS_PATH} "
        "-srcstorepass '{PKCS_PWD}' -deststorepass '{PKCS_PWD}' -noprompt",
        shell=True, stdout=stdout_fw
    )
    r = p.wait()
    if r != 0:
        log(f'!!!Import to jks failed.', stdout_fw)
        raise RuntimeError
    log(f'Import to jks result={p.returncode}', stdout_fw)

    p = subprocess.Popen(
        f'{BREW_BIN} services restart jenkins',
        shell=True, stdout=stdout_fw
    )
    r = p.wait()
    if r != 0:
        log(f'!!!Restart Jenkins  failed.', stdout_fw)
        raise RuntimeError
    log(f'Restart Jenkins result={p.returncode}', stdout_fw)


def main(stdout_fw):
    # check cer changes
    p = subprocess.Popen(f'{MD5_BIN} {ACME_SH_DIR}/{DOMAIN}/{DOMAIN}.cer',
                         shell=True, stdout=subprocess.PIPE)
    r = p.stdout.readlines()
    current_md5_str = r[0].decode('utf-8')

    md5_file = f'{UPDATE_CERT_WORKING_DIR}/{DOMAIN}.cer.md5'
    with open(md5_file, 'r') as fr:
        existing_md5_str = ''.join([i for i in fr.readlines()])

    log(f"current md5 = {current_md5_str}", stdout_fw)
    log(f"existing md5 = {existing_md5_str}", stdout_fw)
    log(f"md5 is equivalent = {existing_md5_str == current_md5_str}", stdout_fw)

    if current_md5_str != existing_md5_str:
        log("Start importing pkcs to jks and restart Jenkins", stdout_fw)
        import_jks_and_restart_jenkins(stdout_fw)
        # update md5
        with open(md5_file, 'w') as fw:
            fw.write(current_md5_str)

    else:
        log("Nothing changed. Skipping.", stdout_fw)


if __name__ == '__main__':
    with open(f'{UPDATE_CERT_WORKING_DIR}/update_cert_for_jenkins.log', 'a') as fw:
        main(fw)
