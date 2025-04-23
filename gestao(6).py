import sqlite3

conn = sqlite3.connect('recebimentos.db')
c = conn.cursor()

# Cria tabela
c.execute('''CREATE TABLE recebimentos
             (data TEXT, dinheiro REAL, cartao REAL, pix REAL)''')

# Insere dados
dados = [
    ('2024-04-01', 450.00, 1250.00, 380.00),
    ('2024-04-02', 520.00, 1580.00, 420.00),
    ('2024-04-03', 380.00, 1420.00, 510.00),
    ('2024-04-04', 610.00, 2100.00, 590.00),
    ('2024-04-05', 490.00, 1850.00, 470.00),
    ('2024-04-06', 720.00, 2450.00, 680.00),
    ('2024-04-07', 550.00, 1650.00, 520.00)
]

c.executemany("INSERT INTO recebimentos VALUES (?, ?, ?, ?)", dados)

conn.commit()
conn.close()
