require('dotenv').config();
const express = require('express');
const mysql = require('mysql2');
const cors = require('cors');
const path = require('path');
const app = express();
const { exec } = require('child_process');
const port = parseInt(process.env.NODE_PORT) || 8080;
const host = process.env.NODE_HOST || '0.0.0.0';

// CORS 옵션 세부 설정
const corsOptions = {
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
};
app.use(cors(corsOptions));

// JSON 파싱 미들웨어 추가
app.use(express.json());

// 프론트엔드에 API 설정을 동적으로 주입하는 config.js 엔드포인트
app.get('/js/config.js', (req, res) => {
  res.setHeader('Content-Type', 'application/javascript');
  res.send(`
const API_CONFIG = {
  FLASK_API: '${process.env.FLASK_API_URL || 'http://localhost:5050'}',
  NODE_API: ''
};
`);
});

// 정적 파일 서빙 미들웨어 추가 (HTML, CSS, JS 등)
app.use(express.static(path.join(__dirname, 'pubulic')));

// 데이터베이스 연결 풀 사용 (환경변수에서 로드)
const pool = mysql.createPool({
  host: process.env.MYSQL_HOST || 'localhost',
  user: process.env.MYSQL_USER || 'root',
  password: process.env.MYSQL_PASSWORD || '',
  database: process.env.MYSQL_DATABASE || 'db',
  connectionLimit: parseInt(process.env.MYSQL_CONNECTION_LIMIT) || 40
});

// HTML 라우트 추가
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'pubulic', 'index.html'));
});

app.get('/index.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'pubulic', 'index.html'));
});

app.get('/chart.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'pubulic', 'chart.html'));
});

app.get('/tables.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'pubulic', 'tables.html'));
});

app.get('/tables_copy.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'pubulic', 'tables_copy.html'));
});

app.get('/test.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'pubulic', 'test.html'));
});

app.get('/craw.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'pubulic', 'craw.html'));
});

app.get('/run_script', (req, res) => {
  exec('python steelin_ver2.py', { maxBuffer: 1024 * 1024 * 10 }, (error, stdout, stderr) => {
    if (error) {
      console.error(`스크립트 실행 오류: ${error.message}`);
      console.error(`stderr: ${stderr}`);
      return res.status(500).send('스크립트 실행 중 오류가 발생했습니다.');
    }

    try {
      const data = JSON.parse(stdout); // JSON 파싱
      if (!Array.isArray(data)) {
        throw new Error('잘못된 데이터 형식입니다.');
      }

      pool.getConnection((err, connection) => {
        if (err) {
          console.error('DB 연결 오류:', err);
          return res.status(500).send('데이터베이스 연결 오류가 발생했습니다.');
        }

        const sqlCheck = 'SELECT COUNT(*) AS count FROM kisco WHERE Link = ?';
        const sqlInsert = 'INSERT INTO kisco (Date, Title, Content, Link, label) VALUES (?, ?, ?, ?, ?)';

        const promises = data.map(row => {
          return new Promise((resolve, reject) => {
            connection.query(sqlCheck, [row.Link], (error, results) => {
              if (error) {
                return reject(error);
              }
              if (results[0].count > 0) {
                return resolve(); // 중복 데이터는 삽입하지 않음
              }
              connection.query(sqlInsert, [row.Date, row.Title, row.Content, row.Link, row.label], (error, results) => {
                if (error) {
                  return reject(error);
                }
                resolve(results);
              });
            });
          });
        });

        Promise.all(promises)
          .then(() => {
            connection.release();
            res.status(200).send('업데이트 완료되었습니다.');
          })
          .catch((error) => {
            connection.release();
            console.error('데이터 삽입 오류:', error);
            res.status(500).send('데이터 삽입 중 오류가 발생했습니다.');
          });
      });
    } catch (parseError) {
      console.error(`출력 파싱 오류: ${parseError.message}`);
      res.status(500).send('스크립트 출력 처리 중 오류가 발생했습니다.');
    }
  });
});

app.get('/data', (req, res) => {
  const limit = parseInt(req.query.length, 10) || 10; // 한 페이지에 보여줄 데이터 개수
  const offset = parseInt(req.query.start, 10) || 0;  // 시작 인덱스

  pool.getConnection((err, connection) => {
      if (err) {
          console.error('DB 연결 오류:', err);
          return res.status(500).json({ error: 'Database connection error' });
      }

      const query = `SELECT 
                          COALESCE(Title, '제목 없음') AS Title,
                          COALESCE(Content, '내용 없음') AS Content,
                          Link,
                          Date
                     FROM kisco 
                     ORDER BY Date DESC 
                     LIMIT ? OFFSET ?`;

      connection.query(query, [limit, offset], (error, results) => {
          connection.release();
          if (error) {
              console.error('쿼리 실행 오류:', error);
              return res.status(500).json({ error: 'Query execution error' });
          }

          const countQuery = `SELECT COUNT(*) AS total FROM kisco`;
          connection.query(countQuery, (error, countResult) => {
              if (error) {
                  console.error('레코드 수 쿼리 오류:', error);
                  return res.status(500).json({ error: 'Count query execution error' });
              }

              const totalRecords = countResult[0]?.total || 0;

              res.json({
                  draw: req.query.draw || 0,
                  recordsTotal: totalRecords,
                  recordsFiltered: totalRecords,
                  data: results || [] // 데이터가 없으면 빈 배열 반환
              });
          });
      });
  });
});

app.post('/get-date', (req, res) => {
  const { date } = req.body;

  // 요청 로그 출력
  console.log(`Received request for date: ${date}`);

  if (!date) {
      console.error('No date provided');
      return res.status(400).json({ error: 'No date provided' });
  }

  const query = `
      SELECT COUNT(*) AS today_scrap_count
      FROM kisco
      WHERE Date = ?;
  `;

  pool.getConnection((err, connection) => {
      if (err) {
          console.error('DB 연결 오류:', err);
          return res.status(500).json({ error: 'Database connection error' });
      }

      connection.query(query, [date], (error, results) => {
          connection.release();
          if (error) {
              console.error('쿼리 실행 오류:', error);
              return res.status(500).json({ error: 'Query execution error' });
          }

          // 쿼리 결과 로그 출력
          console.log(`Query results for date ${date}:`, results);

          const todayScrapCount = results[0]?.today_scrap_count || 0;

          // 결과 로그 출력
          console.log(`Scrap count for ${date}: ${todayScrapCount}`);

          res.json({ today_scrap_count: todayScrapCount });
      });
  });
});

app.post('/get-news', (req, res) => {
  const { date } = req.body;

  if (!date) {
      return res.status(400).json({ error: 'No date provided' });
  }

  const query = `
      SELECT SUBSTRING(Title, 1, 20) AS Title, Date
      FROM kisco
      WHERE DATE(Date) = ?
      ORDER BY Date DESC
      LIMIT 6;
  `;

  pool.getConnection((err, connection) => {
      if (err) {
          console.error('DB 연결 오류:', err);
          return res.status(500).json({ error: 'Database connection error' });
      }

      connection.query(query, [date], (error, results) => {
          connection.release();
          if (error) {
              console.error('쿼리 실행 오류:', error);
              return res.status(500).json({ error: 'Query execution error' });
          }

          // 결과 반환
          res.json({ news: results });
      });
  });
});

// 에러 핸들링 미들웨어
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: '서버 내부 오류',
    details: err.message
  });
});

// 서버 시작
app.listen(port, host, () => {
  console.log(`서버가 http://${host}:${port}에서 실행 중`);
});

// 프로세스 전역 예외 처리
process.on('uncaughtException', (err) => {
  console.error('처리되지 않은 예외:', err);
});