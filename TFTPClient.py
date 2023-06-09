#!/usr/bin/python3
#통신을 위한 socket 라이브러리
import socket
#파라미터를 받기 위한 라이브러리
import argparse
#메세지를 TFTP 규격에 맞게 포맷팅하기 위한 라이브러리
from struct import pack

#기본 포트는 69
DEFAULT_PORT = 69
#헤더를 제외한 데이터 블록 사이즈
BLOCK_SIZE = 512
DEFAULT_TRANSFER_MODE = 'netascii'
#opcode와 mode
OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}
MODE = {'netascii': 1,'octet': 2, 'mail': 3}
#에러 코드
ERROR_CODE = {
    0: "Not defined, see error message (if any).",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
}

#WRQ 메시지 전송 메소드
def send_wrq(filename, mode):
    #TFTP 규격에 맞게 포맷팅
    #  2 bytes   string    1byte string 1byte
    # ------------------------------------------------
    # | Opcode | Filename |  0  | Mode |  0  |
    # ------------------------------------------------

    format = f'>h{len(filename)}sB{len(mode)}sB'
    wrq_message = pack(format, OPCODE['WRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(wrq_message, server_address)

#RRQ 메시지 전송 메소드
def send_rrq(filename, mode):
    # TFTP 규격에 맞게 포맷팅
    #  2 bytes   string    1byte string 1byte
    # ------------------------------------------------
    # | Opcode | Filename |  0  | Mode |  0  |
    # ------------------------------------------------
    format = f'>h{len(filename)}sB{len(mode)}sB'
    rrq_message = pack(format, OPCODE['RRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(rrq_message, server_address)

#ACK 메시지 전송 메소드
def send_ack(seq_num, server):
    # TFTP 규격에 맞게 포맷팅
    #  2 bytes   2 bytes
    # ---------------------
    # | Opcode | Block  # |
    # ---------------------
    format = f'>hh'
    ack_message = pack(format, OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server)

#DATA 메시지 전송 메소드
def send_data(seq_num, data, server):
    # TFTP 규격에 맞게 포맷팅
    #   2bytes    2bytes    n bytes
    # ----------------------------------
    # | Opcode | Block  # |   Data     |
    # ----------------------------------
    format = f">hh{len(data)}s"
    data_message = pack(format, OPCODE['DATA'], seq_num, data)
    sock.sendto(data_message, server)

#get 동작 메소드
def receive_file():
    #RRQ 메시지를 만들어 전송
    send_rrq(filename, mode)
    #받을 파일을 생성/오픈 함
    file = open(filename, "wb")

    while True:
        #받을 데이터는 헤더 4 byte, 데이터 512 byte 이므로 516 byte를 받는다
        data, server = sock.recvfrom(516)
        #opcode를 추출함
        opcode = int.from_bytes(data[:2], 'big')
        #opcode가 DATA일 경우
        if opcode == OPCODE['DATA']:
            #시퀀스 넘버를 추출함
            seq_number = int.from_bytes(data[2:4], 'big')
            #받은 데이터에 대한 ACK 메시지 전송
            send_ack(seq_number, server)
        #opcode가 에러코드이면 에러코드를 출력하고 종료 함
        elif opcode == OPCODE['ERROR']:
            error_code = int.from_bytes(data[2:4], byteorder='big')
            print("\n"+ERROR_CODE[error_code])
            break
        # 이 외의 오류가 일어나면 종료 함
        else:
            print(f"\nUnknown Error")
            break
        #받은 메시지에서 데이터 블럭을 추출함
        file_block = data[4:]
        print(file_block.decode())
        #전에 열었던 파일에 데이터를 씀
        file.write(file_block)
        #받은 데이터 블록 사이즈가 512보다 작으면 마지막 메시지임을 뜻 함
        if len(file_block) < BLOCK_SIZE:
            print(len(file_block))
            #파일을 닫고 종료함
            file.close()
            break

#put 동작 메소드
def send_file():
    try:
        #로컬 디렉토리에서 파일을 오픈 함
        file = open(filename, "rb")
        print(f"\nSend WRQ")
        #WRQ 메시지를 만들어 전송
        send_wrq(filename, mode)
        print(f"\nListening...")
        #WRQ에 대한 응답을 받음
        data, server = sock.recvfrom(4)
        #응답 메시지를 받으면 opcode를 추출함
        opcode = int.from_bytes(data[:2], 'big')
        #opcode가 ACK일 경우 파일 전송을 시작함
        if (opcode == OPCODE['ACK']):
            print(f"\nRecived ACK")
            #전송할 시퀀스 넘버를 1로 초기화 함
            seq_num = 1
            while True:
                #TFTP의 헤더를 제외한 전송할 수 있는 데이터 사이즈는 512byte이므로 512byte만큼 읽음
                line = file.read(BLOCK_SIZE)
                #더 이상 읽을 내용이 없으면 반복문에서 빠져나옴
                if line == b'':
                    break
                #헤더와 데이터를 포장하여 서버에 전송 함
                print(f"\nSend to : {server}, [Block Number : {seq_num}], [Data : {line}]")
                send_data(seq_num, line, server)
                #전송한 데이터에 대하여 응답 메시지를 받음
                data, server = sock.recvfrom(4)
                #응답이 오면 opcode와 시퀀스 넘버를 추출함
                opcode = int.from_bytes(data[:2], 'big')
                response_seq_num = int.from_bytes(data[2:], 'big')
                #opcode가 ACK이고 받음 시퀀스 넘버가 내가 보낸 시퀀스 넘버와 일치하면
                if opcode == OPCODE['ACK'] and response_seq_num == seq_num:
                    #시퀀스 넘버를 +1 하고 다음 반복을 시작 함
                    seq_num += 1
                    continue
                #opcode가 에러코드이면 에러코드를 출력하고 종료 함
                elif opcode == OPCODE['ERROR']:
                    error_code = int.from_bytes(data[2:4], byteorder='big')
                    print("\n"+ERROR_CODE[error_code])
                    break
                #이 외의 오류가 일어나면 종료 함
                else:
                    print(f"\nUnknown Error")
                    break
        else:
            print(f"Something is Error")
        print(f"\nDone!")
        #열었던 파일을 닫아줌
        file.close()
    except:
        #클라이언트에 파일이 존재하지 않으면 오류를 표시하고 종료함
        print(f"\nFile Not Found!")



#파일 실행을 위한 파라미터 관련 코드
parser = argparse.ArgumentParser(description='TFTP client program')
parser.add_argument(dest="host", help="Server IP address", type=str)
parser.add_argument(dest="action", help="get or put a file", type=str)
parser.add_argument(dest="filename", help="name of file to transfer", type=str)
#포트 번호는 선택으로 넣을 수 있다.
parser.add_argument("-p", "--port", dest="port", action="store", type=int)
args = parser.parse_args()

#실행 할 때 받은 파라미터를 변수로 저장
filename = args.filename
server_ip = args.host
server_port = DEFAULT_PORT
server_address = (server_ip, server_port)
#서버와 통신에 사용할 소켓을 만듬
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#모드는 netascii모드를 고정으로 함
mode = DEFAULT_TRANSFER_MODE

#파라미터로 받은 액션에 대한 분기
if args.action == "get":
    receive_file()
elif args.action == "put":
    send_file()


