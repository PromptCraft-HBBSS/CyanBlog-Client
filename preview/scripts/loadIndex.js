fetch('/latest-entries?limit=3')
.then(res => res.json())
.then((res) => {
    const list = document.getElementById('latest-list');
    list.innerHTML = '';
    res.forEach(element => {
        const entry = document.createElement('li');
        const link = document.createElement('a');
        link.href = `/entry/${element.filename}`
        link.textContent = element.filename || `Diary Entry #${element.id}`;
        if (element.locked) {
            element.textContent += " (Locked)"
        }
        entry.appendChild(link);
        list.appendChild(entry);
    });
})