---
title: "{{ replace .Name "-" " " | title }}"
date: {{ now.Format "2006-01-02" }}
url: /{{ .Name }}/
description: ""
tags: [strategy, beginner]
featured_image: "/images/{{ .Name }}.webp"
images: [""]
categories: Strategy
comment: true
draft: true
---
<!--more-->