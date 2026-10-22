for (const element of document.querySelectorAll("time[datetime]")) {
  const date = new Date(element.dateTime);
  if (!Number.isNaN(date.getTime())) {
    element.textContent = new Intl.DateTimeFormat("zh-CN", {
      year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
    }).format(date);
    element.title = "本地时间";
  }
}
