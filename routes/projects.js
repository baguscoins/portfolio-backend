
const express = require('express');
const router = express.Router();
const Project = require('../models/Project');

router.get('/', async (req, res) => {
  const projects = await Project.find();
  res.json(projects);
});

module.exports = router;
