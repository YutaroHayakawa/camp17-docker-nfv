#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <net/ethernet.h>
#include <netinet/ether.h>
#include <sys/epoll.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <poll.h>

#define BUF_SIZE 1500

struct eth {
  uint8_t dst[6];
  uint8_t src[6];
  uint32_t vlan;
  uint16_t type;
};

struct ipv4 {
  uint8_t verihl;
  uint8_t dscp:6;
  uint8_t __unused:2;
  uint16_t tot_len;
  uint16_t ident;
  uint16_t flags:4;
  uint16_t offset:12;
  uint8_t ttl;
  uint8_t proto;
  uint16_t check;
  uint32_t src;
  uint32_t dst;
};

void die(const char *msg) {
  perror(msg);
  exit(EXIT_FAILURE);
}

static int set_pmcs_socket(const char *iface)
{
  int sockfd, err;
  struct ifreq ifr;
  struct packet_mreq mreq;
  struct sockaddr_ll addr;

  /* create socket */
  sockfd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
  if(sockfd < 0){
      perror("socket error");
      return -1;
  }

  /* get interface index */
  memset(&ifr, 0, sizeof(ifr));
  strncpy(ifr.ifr_name, iface, IFNAMSIZ);
  if(ioctl(sockfd, SIOCGIFINDEX, &ifr) < 0){
      perror("ioctl error");
      close(sockfd);
      return -1;
  }

  /* set promiscuous mode */
  memset(&mreq, 0, sizeof(mreq));
  mreq.mr_type = PACKET_MR_PROMISC;
  mreq.mr_ifindex = ifr.ifr_ifindex;
  if(setsockopt(sockfd, SOL_PACKET, PACKET_ADD_MEMBERSHIP,
          (void *)&mreq, sizeof(mreq)) < 0){
      perror("setsockopt error");
      close(sockfd);
      return -1;
  }

  memset(&addr, 0, sizeof(addr));
  addr.sll_family = AF_PACKET;
  addr.sll_protocol = htons(ETH_P_ALL);
  addr.sll_ifindex = if_nametoindex(iface);
  err = bind(sockfd, (struct sockaddr *)&addr, sizeof(addr));
  if (err < 0) {
    die("bind");
  }

  return sockfd;
}

int main(void) {
  int sock1, sock2, err;
  uint8_t buf[BUF_SIZE];

  sock1 = set_pmcs_socket("eth0");
  if (sock1 < 0) {
    die("socket");
  }

  sock2 = set_pmcs_socket("eth1");
  if (sock2 < 0) {
    die("socket");
  }

  struct pollfd fds[2];

  memset(&fds, 0, sizeof(fds));

  fds[0].fd = sock1;
  fds[0].events = POLLIN | POLLERR;

  fds[1].fd = sock2;
  fds[1].events = POLLIN | POLLERR;

  ssize_t rs, ss;
  for (;;) {
    struct eth *e;
    struct ipv4 *ip;

    err = poll(fds, 2, -1);
    if (err < 0) {
      die("poll");
    }

    printf("Got packet!\n");

    if (fds[0].revents & POLLIN) {
      rs = recv(sock1, buf, BUF_SIZE, 0);
      if (rs < 0) {
        die("recv");
      }

      e = (struct eth*)buf;
      ip = (struct ipv4 *)(e + 1);

      printf("Got packet! DSCP: %x\n", ip->dscp);

      ss = send(sock2, buf, rs, MSG_DONTROUTE);
      if (ss < 0) {
        die("send");
      }
    }

    if (fds[1].revents & POLLIN) {
      rs = recv(sock2, buf, BUF_SIZE, 0);
      if (rs < 0) {
        die("recv");
      }

      e = (struct eth*)buf;
      ip = (struct ipv4 *)(e + 1);
      printf("Got packet! DSCP: %x\n", ip->dscp);

      ss = send(sock1, buf, rs, MSG_DONTROUTE);
      if (ss < 0) {
        die("send");
      }
    }
  }

  return EXIT_SUCCESS;
}
