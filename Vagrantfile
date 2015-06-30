# -*- mode: ruby -*-
# vi: set ft=ruby :

# This Vagrantfile is to enable quick setup in development. It attempts to mimic
# the current live server where that makes sense, and therefore starts
# from CentOS 5.11

Vagrant.configure(2) do |config|
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  config.vm.box = "chef/centos-5.11"

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine.
  config.vm.network "forwarded_port", guest: 8000, host: 9000

  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.synced_folder "../", "/vagrant"

  config.ssh.forward_agent = true

  config.vm.provision :shell, path: "bootstrap-redhat.sh"

  # Install virtualenv and deps, but as normal user. This isn't really provisioning,
  # but reduces complexity of dev setup.
  config.vm.provision :shell, path: "bootstrap-venv.sh", privileged: false

end
