import sys
import socket
import ssl
import re

def send_request(protocol, host, path):
    port = 443 if protocol == 'https' else 80
    try:
        s = socket.create_connection((host, port))
        if protocol == 'https':
            s = ssl.wrap_socket(s)
    except (socket.gaierror, ConnectionRefusedError):
        print("Unable to connect to the host.")
        sys.exit(1)

    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    s.send(request.encode())

    response = []
    while True:
        data = s.recv(1024)
        if not data:
            break
        response.append(data)
        
    s.close()
    return b''.join(response)


def process_response(response, host):
    try:
        header, body = response.split(b'\r\n\r\n', 1)
    except ValueError:
        header = response
        body = b''
    
    header = header.decode(errors='replace')
    body = body.decode(errors='replace')

    info = {
        'website': host,
        'supports_http2': 'no',
        'cookies': [],
        'password_protected': 'no',
        'redirect_url': None
    }

    for line in header.split('\r\n'):
        if line.lower().startswith('set-cookie:'):
            cookie_str = line[len('Set-Cookie: '):]
            cookie_info = {'name': None, 'expires': None, 'domain': None}
            
            parts = cookie_str.split(';')
            for i, part in enumerate(parts):
                part = part.strip()
                if i == 0:
                    cookie_info['name'] = part.split('=')[0]
                elif part.lower().startswith('expires='):
                    cookie_info['expires'] = part[len('expires='):]
                elif part.lower().startswith('domain='):
                    cookie_info['domain'] = part[len('domain='):]
            
            info['cookies'].append(cookie_info)
        
        elif line.lower().startswith('location:'):
            info['redirect_url'] = line[len('Location: '):].strip()
        
        elif '401 unauthorized' in line.lower():
            info['password_protected'] = 'yes'
    
    return info


def print_results(info):
    print(f"website: {info['website']}")
    print(f"1. Supports http2: {info['supports_http2']}")
    print("2. List of Cookies:")
    for cookie in info['cookies']:
        cookie_str = f"cookie name: {cookie['name']}, "
        if cookie['expires']:
            cookie_str += f"expires time: {cookie['expires']}, "
        if cookie['domain']:
            cookie_str += f"domain name: {cookie['domain']}"
        print(cookie_str)
    print(f"3. Password-protected: {info['password_protected']}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 smartclient.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    protocol, _, hostpath = url.partition('://')
    if not protocol or not hostpath:
        protocol = 'https'  # default to https if not specified
        host, _, path = url.partition('/')
    else:
        host, _, path = hostpath.partition('/')
    
    path = '/' + path  # reconstructing path with leading '/'
    response = send_request(protocol, host, path)
    info = process_response(response, host)
    print_results(info)
    
    if info['redirect_url']:
        print("Following redirect...")
        main_url = info['redirect_url']
        protocol, _, hostpath = main_url.partition('://')
        host, _, path = hostpath.partition('/')
        path = '/' + path
        response = send_request(protocol, host, path)
        info = process_response(response, host)
        print_results(info)

if __name__ == "__main__":
    main()
