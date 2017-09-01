FROM ubuntu:xenial

RUN apt-get -y update && apt-get -y upgrade
RUN apt-get install -y build-essential libpcap-dev libpcre3-dev libdumbnet-dev bison flex wget \
libnetfilter-queue-dev zlib1g-dev liblzma-dev openssl libssl-dev libnghttp2-dev

RUN mkdir /snort_src
WORKDIR /snort_src

RUN wget https://snort.org/downloads/snort/daq-2.0.6.tar.gz
RUN tar -xvzf daq-2.0.6.tar.gz

WORKDIR daq-2.0.6
RUN ./configure
RUN make
RUN make install

WORKDIR /snort_src
RUN wget https://snort.org/downloads/snort/snort-2.9.9.0.tar.gz
RUN tar -xvzf snort-2.9.9.0.tar.gz

WORKDIR snort-2.9.9.0
RUN ./configure --enable-sourcefire
RUN make
RUN make install
RUN ldconfig
RUN ln -s /usr/local/bin/snort /usr/sbin/snort

# Create the Snort directories:
RUN mkdir /etc/snort
RUN mkdir /etc/snort/rules
RUN mkdir /etc/snort/rules/iplists
RUN mkdir /etc/snort/preproc_rules
RUN mkdir /usr/local/lib/snort_dynamicrules
RUN mkdir /etc/snort/so_rules

# Create some files that stores rules and ip lists
RUN touch /etc/snort/rules/iplists/black_list.rules
RUN touch /etc/snort/rules/iplists/white_list.rules
RUN touch /etc/snort/rules/local.rules
RUN touch /etc/snort/sid-msg.map

# Create our logging directories:
RUN mkdir /var/log/snort
RUN mkdir /var/log/snort/archived_logs

# Adjust permissions:
RUN chmod -R 5775 /etc/snort
RUN chmod -R 5775 /var/log/snort
RUN chmod -R 5775 /var/log/snort/archived_logs
RUN chmod -R 5775 /etc/snort/so_rules
RUN chmod -R 5775 /usr/local/lib/snort_dynamicrules

WORKDIR /snort_src/snort-2.9.9.0/etc/

RUN cp *.conf* /etc/snort
RUN cp *.map /etc/snort
RUN cp *.dtd /etc/snort
WORKDIR /snort_src/snort-2.9.9.0/src/dynamic-preprocessors/build/usr/local/lib/snort_dynamicpreprocessor/
RUN cp * /usr/local/lib/snort_dynamicpreprocessor/

WORKDIR /usr/local/src
RUN wget https://www.snort.org/rules/snortrules-snapshot-2990.tar.gz?oinkcode=f337d856cfda57c9b6b691bede32518fe46afb1c -O snortrules-snapshot-2990.tar.gz

WORKDIR /etc/snort
RUN tar zxvf /usr/local/src/snortrules-snapshot-2990.tar.gz
RUN cp ./etc/* .
RUN cp /snort_src/snort-2.9.9.0/etc/* .
RUN rm /etc/snort/Makefile*

RUN cp /etc/snort/so_rules/precompiled/Ubuntu-12-04/x86-64/2.9.9.0/* /usr/local/lib/snort_dynamicrules/

ADD config/snort.conf /etc/snort/snort.conf
