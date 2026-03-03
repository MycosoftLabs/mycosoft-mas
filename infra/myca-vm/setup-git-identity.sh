#!/bin/bash
# Setup MYCA's git identity on VM 191
# Run once during provisioning

set -e

echo "Configuring MYCA git identity..."

git config --global user.name "MYCA"
git config --global user.email "myca@mycosoft.org"
git config --global init.defaultBranch main
git config --global pull.rebase false

echo "Git identity configured:"
echo "  Name:  $(git config --global user.name)"
echo "  Email: $(git config --global user.email)"

# Setup SSH key for GitHub (if not exists)
if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "Generating SSH key for GitHub..."
    ssh-keygen -t ed25519 -C "myca@mycosoft.org" -f ~/.ssh/id_ed25519 -N ""
    echo ""
    echo "Add this public key to GitHub as MYCA's deploy key:"
    cat ~/.ssh/id_ed25519.pub
fi

echo ""
echo "MYCA git identity setup complete."
